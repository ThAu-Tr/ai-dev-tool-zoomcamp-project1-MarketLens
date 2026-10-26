# Observability: local Grafana and production telemetry

Run commands below from the repository root. The local observability stack is isolated from the normal Docker setup.

### Local dashboard observability demo (issue #38)

The isolated observability Compose project uses these default addresses:

| Service | Local address | Purpose |
| --- | --- | --- |
| Regular MarketLens app | `http://localhost:8000` | Standard local Compose setup (`compose.yaml`) |
| Observability demo app | `http://localhost:8001` | Isolated dashboard for alert and recovery testing |
| Grafana | `http://localhost:3000` | Metrics, traces, logs and local alerts |
| On-call receiver feed | `http://127.0.0.1:8081` | Loopback-only sanitized events consumed by the host agent |
| Prometheus | `http://localhost:9090` | Local metrics storage and queries |

Override the demo/receiver ports through `MARKETLENS_PORT`/`ONCALL_FEED_PORT` in `.env.observability`. The on-call agent runs separately on the host. **Never fault-inject the normal application or production database.**


Only `GET /api/dashboard` is instrumented: React sends W3C `traceparent`, FastAPI records the request and PostgreSQL read spans, and request metrics/logs share the trace ID. Other routes are not instrumented. Local export uses collector gRPC; configured Grafana Cloud export uses OTLP HTTP/protobuf.

Telemetry is deliberately limited to service/environment, route template, method, status, duration, outcome, exception class, and trace/span IDs. It does not record headers, query strings, SQL text or parameters, exception messages, request/response bodies, asset or article identifiers, holdings, quantities, or values. The isolated local stack stores telemetry in local Docker volumes with 24-hour retention for traces, logs, and metrics; Grafana uses the local demo login `admin` / `admin`. By default no telemetry is sent outside the local stack. Direct Grafana Cloud export is enabled only when explicitly configured in the deployed service environment.

With Docker Compose installed, run these commands in PowerShell from the repository root:

```powershell
Copy-Item .env.observability.example .env.observability
# On first setup only; do not overwrite an existing .env.observability.
# Replace the example POSTGRES_PASSWORD in .env.observability.
# EODHD_API_KEY, MARKETAUX_API_KEY and OPENAI_API_KEY are optional:
# leave them blank for the Grafana/on-call demo; set them for provider features.
# Keep the example's local OpenTelemetry and port settings for the demo.
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml up --build -d
curl.exe -i http://localhost:8001/api/dashboard
```

This project uses its own PostgreSQL volume and seeded demo user; the dashboard should return HTTP 200 without provider calls. Provider keys are optional and passed only to the app, not the on-call receiver; add them to `.env.observability` for live refresh features.

To produce a controlled database failure only in this isolated project, run:

```powershell
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml stop db
curl.exe -i http://localhost:8001/api/dashboard
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml start db
```

The stopped database produces HTTP 500. In [Grafana Explore](http://localhost:3000/explore) (`admin` / `admin`), inspect Prometheus `marketlens_dashboard_requests_total` and `marketlens_dashboard_duration_milliseconds_bucket`, Tempo spans, and Loki `dashboard_request` logs. Correlate by `trace_id`; the trace includes `dashboard.repository.read` and exception class but no raw database error message.

Recorded evidence: Prometheus reported `200/success` and `500/failure`; Tempo and Loki showed corresponding spans/logs with matching redacted trace IDs (`961f8f98…`, `a4c39f9a…`).

Stop the demo with `docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml down`. Add `--volumes` to remove its isolated data and telemetry. The stack is bound to localhost and must not be exposed as a production service.


### Grafana Cloud export for the deployed dashboard

The deployed app can export the same dashboard-only signals directly to Grafana Cloud; it does not need the local collector. In Grafana Cloud, open your stack's **Configure → OpenTelemetry** setup and copy the stack-specific OTLP endpoint and generated authentication header. In Render, add these variables to the MarketLens web service's Environment settings:

| Variable | Value |
| --- | --- |
| `OTEL_ENABLED` | `true` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | The base endpoint from Grafana Cloud, including `/otlp` and excluding `/v1/traces`, `/v1/metrics`, or `/v1/logs` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` |
| `OTEL_EXPORTER_OTLP_HEADERS` | The generated header from Grafana Cloud, formatted as `Authorization=Basic%20<generated-value>` |
| `OTEL_ENVIRONMENT` | `production` |
| `OTEL_METRIC_EXPORT_INTERVAL_MILLIS` | `15000` (optional; defaults to 60000) |

Enter the generated header directly in Render's environment settings; never commit it or send it to Codex. Do not use the local collector hostname in Render. The exporter appends the per-signal path to the base endpoint. Render restarts the service after environment changes. The React app and database configuration do not need changes.

To verify export, load the deployed dashboard at [https://marketlens-dtc.onrender.com/](https://marketlens-dtc.onrender.com/) and reload it once. In the same Grafana Cloud stack, search Tempo for service `marketlens-api` and a recent `GET /api/dashboard` span. Copy its trace ID, then find the log record with body `dashboard_request` and the same `trace_id`. The request metric has that `trace_id` attribute; query `marketlens_dashboard_requests_total{trace_id="<trace-id>"}` in the stack's Metrics/Explore view. Confirm the status/outcome and duration attributes match the trace. Allow up to a minute for metrics at the default export interval. If signals are missing, check Render logs for exporter connection or authorization errors; do not expose the header value in logs or support requests.

