from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import InMemoryLogRecordExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.db import Base, get_session
from app.main import create_app
from app.models import DemoUser
from app.telemetry import DashboardTelemetry


@pytest.fixture
def telemetry_parts() -> Generator[tuple[DashboardTelemetry, InMemorySpanExporter, InMemoryMetricReader, InMemoryLogRecordExporter], None, None]:
    resource = Resource.create({"service.name": "test-marketlens", "deployment.environment": "test"})
    span_exporter = InMemorySpanExporter()
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(SimpleSpanProcessor(span_exporter))
    metric_reader = InMemoryMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    log_exporter = InMemoryLogRecordExporter()
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(log_exporter))
    telemetry = DashboardTelemetry(
        tracer_provider.get_tracer("test"), meter_provider.get_meter("test"), logger_provider.get_logger("test")
    )
    yield telemetry, span_exporter, metric_reader, log_exporter
    tracer_provider.shutdown()
    meter_provider.shutdown()
    logger_provider.shutdown()


@pytest.fixture
def client(telemetry_parts) -> Generator[TestClient, None, None]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app(provider_gateway=object(), telemetry=telemetry_parts[0])
    app.state.test_session_factory = factory

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    engine.dispose()


def test_dashboard_success_correlates_trace_metrics_and_structured_log(client, telemetry_parts) -> None:
    _, span_exporter, metric_reader, log_exporter = telemetry_parts
    with client.app.state.test_session_factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
        session.commit()

    trace_id = "1234567890abcdef1234567890abcdef"
    response = client.get("/api/dashboard", headers={"traceparent": f"00-{trace_id}-0123456789abcdef-01"})

    assert response.status_code == 200
    spans = span_exporter.get_finished_spans()
    assert {span.name for span in spans} == {"GET /api/dashboard", "dashboard.repository.read"}
    assert all(f"{span.context.trace_id:032x}" == trace_id for span in spans)
    assert all(span.attributes["journey.outcome"] == "success" for span in spans)
    metric_points = [point for metric in metric_reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics for point in metric.data.data_points]
    assert any(point.attributes["trace_id"] == trace_id and point.attributes["journey.outcome"] == "success" for point in metric_points)
    log = log_exporter.get_finished_logs()[0].log_record
    assert log.body == "dashboard_request"
    assert log.attributes["trace_id"] == trace_id
    assert log.attributes["journey.outcome"] == "success"


def test_dashboard_failure_records_safe_error_without_query_or_headers(client, telemetry_parts) -> None:
    _, span_exporter, metric_reader, log_exporter = telemetry_parts
    trace_id = "fedcba0987654321fedcba0987654321"
    response = client.get(
        "/api/dashboard?token=api-secret&holding=private-value",
        headers={"traceparent": f"00-{trace_id}-fedcba0987654321-01", "authorization": "Bearer private-token"},
    )

    assert response.status_code == 500
    spans = span_exporter.get_finished_spans()
    assert all(f"{span.context.trace_id:032x}" == trace_id for span in spans)
    failed_span = next(span for span in spans if span.name == "dashboard.repository.read")
    assert failed_span.attributes["journey.outcome"] == "failure"
    assert failed_span.attributes["error.type"] == "RuntimeError"
    log = log_exporter.get_finished_logs()[0].log_record
    metric_points = [point for metric in metric_reader.get_metrics_data().resource_metrics[0].scope_metrics[0].metrics for point in metric.data.data_points]
    records = [str(failed_span.attributes), str(log.attributes), *(str(point.attributes) for point in metric_points)]
    assert all(secret not in " ".join(records) for secret in ("api-secret", "private-value", "private-token"))
    assert log.attributes["journey.outcome"] == "failure"
    assert any(point.attributes["trace_id"] == trace_id and point.attributes["journey.outcome"] == "failure" for point in metric_points)

