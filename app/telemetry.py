from __future__ import annotations

import os
import time
from collections.abc import Callable
from typing import Any

from opentelemetry._logs import SeverityNumber
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Span, Status, StatusCode, Tracer
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter


ROUTE = "/api/dashboard"


class DashboardTelemetry:
    """Safe, low-volume telemetry for the stored dashboard journey only."""

    def __init__(self, tracer: Tracer, meter: Any, logger: Any) -> None:
        self.tracer = tracer
        self.logger = logger
        self.requests = meter.create_counter("marketlens.dashboard.requests", unit="{request}")
        self.failures = meter.create_counter("marketlens.dashboard.failures", unit="{request}")
        self.failure_attributes = {
            "http.route": ROUTE,
            "http.request.method": "GET",
            "http.response.status_class": "5xx",
            "journey.outcome": "failure",
        }
        # Register a zero-valued cumulative series before any failure occurs;
        # Prometheus can then calculate increase() on the first real event.
        self.failures.add(0, self.failure_attributes)
        self.duration = meter.create_histogram("marketlens.dashboard.duration", unit="ms")

    def span(self, name: str, *, context: Any = None):
        return self.tracer.start_as_current_span(name, context=context)

    def record(self, span: Span, *, status_code: int, duration_ms: float) -> None:
        outcome = "success" if status_code < 500 else "failure"
        span.set_attribute("journey.outcome", outcome)
        span.set_attribute("http.response.status_code", status_code)
        if outcome == "failure":
            span.set_status(Status(StatusCode.ERROR))
        context = span.get_span_context()
        trace_id = f"{context.trace_id:032x}" if context.is_valid else ""
        attributes = {
            "http.route": ROUTE,
            "http.request.method": "GET",
            "http.response.status_code": status_code,
            "journey.outcome": outcome,
        }
        # A trace_id dimension is intentional for this low-volume local demo so
        # the metric sample can be joined directly to its trace and log record.
        if trace_id:
            attributes["trace_id"] = trace_id
        self.requests.add(1, attributes)
        if outcome == "failure":
            self.failures.add(1, self.failure_attributes)
        self.duration.record(duration_ms, attributes)
        self.logger.emit(
            timestamp=time.time_ns(),
            observed_timestamp=time.time_ns(),
            severity_number=SeverityNumber.INFO if outcome == "success" else SeverityNumber.ERROR,
            severity_text="INFO" if outcome == "success" else "ERROR",
            body="dashboard_request",
            attributes={**attributes, "trace_id": trace_id},
        )


def create_dashboard_telemetry() -> tuple[DashboardTelemetry, Callable[[], None]]:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    resource = Resource.create(
        {
            "service.name": "marketlens-api",
            "deployment.environment": os.getenv("OTEL_ENVIRONMENT", "local-demo"),
        }
    )

    traces = TracerProvider(resource=resource)
    traces.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True)))
    metrics = MeterProvider(
        resource=resource,
        metric_readers=[
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=endpoint, insecure=True),
                export_interval_millis=max(1000, int(os.getenv("OTEL_METRIC_EXPORT_INTERVAL_MILLIS", "60000"))),
            )
        ],
    )
    logs = LoggerProvider(resource=resource)
    logs.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter(endpoint=endpoint, insecure=True)))

    telemetry = DashboardTelemetry(
        traces.get_tracer("marketlens.dashboard"),
        metrics.get_meter("marketlens.dashboard"),
        logs.get_logger("marketlens.dashboard"),
    )

    def shutdown() -> None:
        traces.shutdown()
        metrics.shutdown()
        logs.shutdown()

    return telemetry, shutdown


class DashboardTelemetryMiddleware:
    """Create one server span and safe metric/log records for GET /api/dashboard."""

    def __init__(self, app: Any, telemetry: DashboardTelemetry) -> None:
        self.app = app
        self.telemetry = telemetry

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope.get("method") != "GET" or scope.get("path") != ROUTE:
            await self.app(scope, receive, send)
            return

        carrier = {
            key.decode("latin1").lower(): value.decode("latin1")
            for key, value in scope.get("headers", [])
            if key.lower() == b"traceparent"
        }
        parent = TraceContextTextMapPropagator().extract(carrier)
        started = time.perf_counter()
        status_code = 500

        async def capture_status(message: dict[str, Any]) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        with self.telemetry.span("GET /api/dashboard", context=parent) as span:
            span.set_attribute("http.route", ROUTE)
            span.set_attribute("http.request.method", "GET")
            try:
                await self.app(scope, receive, capture_status)
            except Exception as error:
                # Record a stable exception class only; exception messages and
                # stack traces may contain SQL, URLs, or credentials.
                span.set_attribute("error.type", type(error).__name__)
                span.set_status(Status(StatusCode.ERROR))
                raise
            finally:
                self.telemetry.record(span, status_code=status_code, duration_ms=(time.perf_counter() - started) * 1000)


def record_database_outcome(span: Span, error: Exception | None = None) -> None:
    """Mark a repository-boundary span without attaching query or exception text."""
    span.set_attribute("db.system", "postgresql")
    span.set_attribute("db.operation.name", "read_dashboard")
    if error is not None:
        span.set_attribute("journey.outcome", "failure")
        span.set_attribute("error.type", type(error).__name__)
        span.set_status(Status(StatusCode.ERROR))
    else:
        span.set_attribute("journey.outcome", "success")

