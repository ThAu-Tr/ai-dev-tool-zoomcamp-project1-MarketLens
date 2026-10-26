from __future__ import annotations

from urllib.parse import urlsplit

import pytest
import requests
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter as GrpcLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter as GrpcMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter as GrpcSpanExporter
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

from app.telemetry import _create_otlp_exporters, create_dashboard_telemetry


def test_default_otlp_exporters_preserve_local_grpc_collector(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_PROTOCOL", raising=False)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
    trace_exporter, metric_exporter, log_exporter = _create_otlp_exporters()

    try:
        assert isinstance(trace_exporter, GrpcSpanExporter)
        assert isinstance(metric_exporter, GrpcMetricExporter)
        assert isinstance(log_exporter, GrpcLogExporter)
        assert trace_exporter._endpoint == "otel-collector:4317"
    finally:
        trace_exporter.shutdown()
        metric_exporter.shutdown()
        log_exporter.shutdown()


def test_http_protobuf_exports_correlated_signals_to_cloud_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, object]] = []
    auth_header = "Basic otlp-test-secret+value="

    def capture_request(
        session: requests.Session,
        method: str,
        url: str,
        **kwargs: object,
    ) -> requests.Response:
        captured.append({"method": method, "url": url, **kwargs})
        response = requests.Response()
        response.status_code = 200
        response._content = b""
        return response

    monkeypatch.setattr(requests.Session, "request", capture_request)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otlp.example.test/otlp/")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_HEADERS", "Authorization=Basic%20otlp-test-secret%2Bvalue%3D")
    monkeypatch.setenv("OTEL_METRIC_EXPORT_INTERVAL_MILLIS", "60000")

    telemetry, shutdown = create_dashboard_telemetry()
    with telemetry.span("GET /api/dashboard") as span:
        expected_trace_id = f"{span.get_span_context().trace_id:032x}"
        telemetry.record(span, status_code=200, duration_ms=7.25)
    shutdown()

    assert {urlsplit(str(call["url"])).path for call in captured} == {
        "/otlp/v1/traces",
        "/otlp/v1/metrics",
        "/otlp/v1/logs",
    }
    assert all(call["method"] == "POST" for call in captured)
    header_maps = [call.get("headers", {}) for call in captured]
    assert all(
        any(key.lower() == "authorization" and value == auth_header for key, value in headers.items())
        for headers in header_maps
    ), [list(headers) for headers in header_maps]

    trace_request = ExportTraceServiceRequest.FromString(
        next(bytes(call["data"]) for call in captured if urlsplit(str(call["url"])).path.endswith("/traces"))
    )
    metrics_request = ExportMetricsServiceRequest.FromString(
        next(bytes(call["data"]) for call in captured if urlsplit(str(call["url"])).path.endswith("/metrics"))
    )
    logs_request = ExportLogsServiceRequest.FromString(
        next(bytes(call["data"]) for call in captured if urlsplit(str(call["url"])).path.endswith("/logs"))
    )

    trace_ids = {
        span.trace_id.hex()
        for resource_spans in trace_request.resource_spans
        for scope_spans in resource_spans.scope_spans
        for span in scope_spans.spans
    }
    metric_trace_ids = {
        attribute.value.string_value
        for resource_metrics in metrics_request.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
        for point in getattr(metric, metric.WhichOneof("data"), ()).data_points
        for attribute in point.attributes
        if attribute.key == "trace_id"
    }
    log_trace_ids = {
        attribute.value.string_value
        for resource_logs in logs_request.resource_logs
        for scope_logs in resource_logs.scope_logs
        for record in scope_logs.log_records
        for attribute in record.attributes
        if attribute.key == "trace_id"
    }

    assert trace_ids == {expected_trace_id}
    assert expected_trace_id in metric_trace_ids
    assert log_trace_ids == {expected_trace_id}
    assert all(auth_header.encode() not in bytes(call["data"]) for call in captured)


@pytest.mark.parametrize(
    ("endpoint", "expected_error"),
    [
        ("file:///tmp/otlp", r"HTTP\(S\) base URL"),
        ("https://user:password@otlp.example.test/otlp", "without embedded credentials"),
        ("https://otlp.example.test/otlp?token=secret", "query or fragment"),
    ],
)
def test_http_endpoint_rejects_credentials_and_non_base_urls(
    endpoint: str, expected_error: str
) -> None:
    with pytest.raises(ValueError, match=expected_error):
        _create_otlp_exporters(endpoint=endpoint, protocol="http/protobuf", raw_headers="Authorization=secret")


def test_invalid_otlp_headers_are_rejected_without_echoing_value() -> None:
    with pytest.raises(ValueError, match="comma-separated key=value headers") as error:
        _create_otlp_exporters(
            endpoint="https://otlp.example.test/otlp",
            protocol="http/protobuf",
            raw_headers="Authorization=secret\r\nInjected: value",
        )
    assert "secret" not in str(error.value)
