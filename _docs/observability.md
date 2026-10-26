# Observability: local Grafana and production telemetry

Run commands below from the repository root. The local observability stack is isolated from the normal Docker setup.

### Local dashboard observability demo (issue #38)

The observability/on-call demo uses a **separate, isolated Docker Compose project** from the normal local application. These are the default local addresses:

| Service | Local address | Purpose |
| --- | --- | --- |
| Regular MarketLens app | `http://localhost:8000` | Standard local Compose setup (`compose.yaml`) |
| Observability demo app | `http://localhost:8001` | Isolated dashboard for alert and recovery testing |
| Grafana | `http://localhost:3000` | Metrics, traces, logs and local alerts |
| On-call receiver feed | `http://127.0.0.1:8081` | Loopback-only sanitized events consumed by the host agent |
| Prometheus | `http://localhost:9090` | Local metrics storage and queries |

The observability app's port and receiver-feed port can be overridden with `MARKETLENS_PORT` and `ONCALL_FEED_PORT` in `.env.observability`. The on-call agent itself runs as a separate host process, not as another public HTTP service. Never fault-inject the normal application or production database.


The optional LGTM stack instruments only the stored `GET /api/dashboard` journey. The React request creates a W3C `traceparent`; FastAPI extracts it and creates the server span, then a repository-boundary span covers the PostgreSQL read. Request count, latency, and a structured request log carry the same trace ID. Other routes and the normal Compose/Render deployment remain uninstrumented. The app exports to the local collector over gRPC by default, or directly to a configured OTLP endpoint over HTTP/protobuf.

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

The separate project has its own PostgreSQL data volume and starts with the migrated demo user, so the dashboard request returns `200` without provider calls. To load live prices in this local demo, add your own `EODHD_API_KEY` to the ignored `.env.observability` file and use the dashboard's **Refresh data** action. The app service passes optional local provider keys through to the app container; no provider calls happen on startup or dashboard reads. Marketaux and OpenAI keys are optional for their respective features. The on-call receiver does not receive these keys.

To produce a controlled database failure only in this isolated project, run:

```powershell
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml stop db
curl.exe -i http://localhost:8001/api/dashboard
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml start db
```

The second request returns `500` while the local database is stopped. Open [Grafana](http://localhost:3000), sign in with the local demo login, and use **Explore**: Prometheus query `marketlens_dashboard_requests_total` shows successes/failures and `marketlens_dashboard_duration_milliseconds_bucket` shows latency; Tempo can open the trace ID; Loki shows `dashboard_request` records. Each signal includes `trace_id`, so paste the same ID into Tempo and compare the matching Loki log and metric sample. The trace shows the `/api/dashboard` span and PostgreSQL read boundary; its status and exception class diagnose failure while the log provides the matching route/outcome, without storing database error text.

Observed on the local demo stack: Prometheus contained one `200/success` sample and one `500/failure` sample; Tempo showed both dashboard traces with the `dashboard.repository.read` child span; Loki showed two `dashboard_request` records. The redacted trace IDs matched between all three signals (`961f8f98…` success, `a4c39f9a…` failure). The [local Grafana Explore UI](http://localhost:3000/explore) opens the provisioned data sources and shows the request metric, traces, and correlated logs.

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

