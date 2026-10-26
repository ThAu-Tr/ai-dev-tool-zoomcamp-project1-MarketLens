# MarketLens

MarketLens is a lightweight investment-monitoring application for everyday investors who want to follow stocks, ETFs, and major indices in one place. It combines price movement with relevant news and carefully qualified AI context so users can understand possible market context without receiving investment advice.

> **Project status:** M4 local MVP accepted ([human acceptance #22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22)); milestone documentation is tracked in [#23](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/23). The M5 Docker deployment is live at [marketlens-dtc.onrender.com](https://marketlens-dtc.onrender.com/); deployment checks are summarized below as owner-reported.

## The problem

Everyday investors often need to piece together price movements, company news, industry developments, and wider events from separate sources. That makes it difficult to understand what may be relevant today or to revisit the context around a past market day.

MarketLens brings those inputs into a combined dashboard and a persistent historical price timeline. It is a monitoring and context tool—not a trading system, portfolio optimiser, or source of investment recommendations.

## What exists today

The locally accepted MVP includes a persisted dashboard; a bounded, curated stock/ETF/index catalogue; Owned and Interested watchlists with purchase lots; followed industries; manual refresh of prices through EODHD and categorized news through Marketaux; qualified, source-linked AI context; and a historical price timeline.

The asset picker searches a local catalogue rather than the provider's entire supported universe. Provider-wide discovery is deferred to [#32](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/32). News per followed industry and automatic redisplay of stored news after refollowing are deferred to [#30](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/30) and [#31](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/31). Human acceptance and the history of corrected defects are recorded in [#22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22).

## Demo

Try the live application at [https://marketlens-dtc.onrender.com/](https://marketlens-dtc.onrender.com/). A separate video or screenshot walkthrough is not currently linked.

## MVP scope

The locally implemented MVP lets a single demo user:

1. Follow Stocks, ETFs, and major Indices as Owned or Interested.
2. Record active purchase lots for Owned Stocks and ETFs.
3. Follow industries and review suggested industries based on tracked assets.
4. Refresh stored prices and categorized news context.
5. Read uncertainty-aware, source-linked AI context summaries.
6. Load historical price movements for individual days within the initial 30-day request window and reuse stored results.

The product deliberately excludes trading, broker integrations, authentication, real-time alerts, full portfolio accounting, crypto, and investment recommendations. Read the complete [product specification](_docs/plan.md).
Historical news, AI-generated historical context, and the complete archived-day experience are post-MVP extensions (#15 and #16). Additional post-MVP requests are tracked in #30–#32.

## Architecture

```text
React frontend
      |
      | HTTP/JSON, OpenAPI contract
      v
FastAPI application
      |
      v
PostgreSQL database
```

The frontend never accesses the database or external providers directly. FastAPI route handlers stay thin; services coordinate workflows, repositories persist data, and provider adapters isolate external integrations.

- [Architecture decisions and data flows](_docs/architecture.md)
- [OpenAPI contract](openapi.yaml)
- [Frontend interaction specification](_docs/frontend-spec.md)

## Project structure

```text
app/                 FastAPI routes, services, repositories, schemas, and models
alembic/             database migrations
frontend/            React/Vite user interface and frontend tests
tests/               backend API and behavior tests
_docs/               product, architecture, workflow, and backlog documentation
openapi.yaml         frontend-backend HTTP contract
```

## Development status and backlog

The MVP is implemented as small, end-to-end GitHub issues rather than separate frontend, backend, and database tasks. Each issue can span UI, API, service logic, persistence, and tests.

- [Current MVP issue board](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues?q=is%3Aissue%20label%3AMVP)
- [Refined local backlog](_docs/backlog.md)
- [Development workflow](_docs/process.md)
- [Representative AI-assisted workflow evidence](_docs/ai-usage-report.md)

## Running checks

Backend tests:

```powershell
uv sync
uv run pytest  # Runs backend unit and integration tests
uv run pytest tests/integration
```

Frontend tests and production build:

```powershell
npm --prefix frontend run test
npm --prefix frontend run build
```

`tests/integration/` is the separately runnable HTTP-to-database workflow suite. It covers adding and managing an asset before reading the dashboard, refreshing and persisting prices/news/AI context before reading the dashboard, and loading then revisiting a historical day. Run it with `uv run pytest tests/integration`; the full backend suite also includes it.

The existing `tests/test_asset_creation.py`, `test_asset_ownership.py`, `test_purchase_lots.py`, `test_refresh.py`, `test_direct_news.py`, `test_ai_context.py`, and `test_timeline.py` contain additional API/service persistence and failure cases. Industry, dashboard, and asset-removal tests likewise exercise HTTP routes against isolated SQLite. `test_asset_catalogue.py` exercises catalogue search through HTTP and tests its service directly; it does not access a database. `test_eodhd_provider.py`, `test_marketaux.py`, and `test_provider_factory.py` focus on provider adapters and composition; they use fakes and do not establish live provider connectivity. Some service and repository logic is tested directly in `test_ai_context.py` and provider-specific tests.

The integration suite uses an isolated in-memory SQLite database and deterministic fake providers, so it makes no live market, news, or AI calls. SQLite test results do not establish PostgreSQL compatibility or real provider integration. Those require the separate manual PostgreSQL/provider smoke checks described below.

## Local development and configuration

**Course assignment / peer review:** MarketLens is a non-commercial educational project. Reviewers who run the app locally create their own EODHD and Marketaux accounts and supply their own API keys in a local `.env` file (copy variable names from `.env.example`). API keys are never included in the repository, and the frontend must not expose them. Provider usage is subject to each reviewer's own account limits and terms.


The backend reads `DATABASE_URL`, `EODHD_API_KEY`, and optional `MARKETAUX_API_KEY` from the process environment. For local use, copy `.env.example` to the ignored `.env` file and add your own keys there; a local `.env` is loaded without overriding variables supplied by the deployment environment. `MARKETAUX_USER_AGENT` can override the request User-Agent. Alembic reads `DATABASE_URL` when applying migrations.

```powershell
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE"
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

To manually smoke-check Marketaux after provider composition is enabled, configure `MARKETAUX_API_KEY` in the backend environment and run one dashboard refresh with one or more tracked symbols. Confirm the refresh completes, then inspect `GET /api/dashboard` for metadata-only articles and source links. The adapter makes separate bounded queries for tracked symbols and followed industries (at most two requests, with three results per request); this live check is optional and must use your own account and quota. Automated tests mock HTTP and do not call Marketaux.

### EODHD smoke check (manual, uses your account)

After migrations, start the backend with `EODHD_API_KEY` set and request `POST /api/refresh` once. Confirm the response succeeds and `GET /api/dashboard` shows an `asOf` timestamp and currency supplied by the provider. Then request `GET /api/timeline?date=YYYY-MM-DD` for one eligible date with known EODHD coverage and confirm its `source` is `newly-loaded`; request the same date again and confirm `source` is `archive`. The second request should not call EODHD. Each refresh may try the intraday endpoint and then fall back to daily closes; use one tracked asset and avoid repeated retries to stay within the free account's daily request limit. Adapter tests mock HTTP and never consume API calls.

The frontend uses `VITE_API_BASE_URL` to select the backend URL. To run the React development server in a separate PowerShell terminal, use:

```powershell
npm --prefix frontend install
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm --prefix frontend run dev
```

The FastAPI backend permits configured frontend origins through `CORS_ALLOWED_ORIGINS` (default `http://localhost:5173`; see `.env.example`). If using another frontend origin, explicitly configure it. Keep EODHD, Marketaux, and OpenAI keys on the backend only. Apply `uv run alembic upgrade head` after updating the application code and before starting the backend.

// TODO (M8): Complete the local setup guide: add PostgreSQL installation/database/user provisioning and prerequisite steps, then independently verify the documented backend startup, Alembic migrations, frontend API URL/CORS configuration, and frontend startup from a clean checkout. Commands are documented but the complete clean-start procedure has not been verified.

## Testing and quality

The project adds tests with each completed vertical feature. Tests use deterministic local data and must not call live market, news, or AI services.

## Important design decisions

- **Simple deployment shape:** one React frontend, one FastAPI application, and PostgreSQL; no queue, cache service, scheduler, microservices, or authentication for the MVP.
- **Contract-first boundary:** [openapi.yaml](openapi.yaml) describes the API expected by the frontend.
- **Single demo user:** data carries an ownership relationship so authentication can be added later without restructuring the core model.
- **Exact financial values:** money and quantities are represented as exact decimals rather than binary floating-point values.
- **Safety:** AI-produced context must be uncertainty-aware, link to supporting sources, and never give investment advice or make definitive causal claims.

## Limitations and future work

The MVP supports one demo user, a bounded local instrument catalogue and provider-dependent market/news/AI coverage. An article or AI summary is not guaranteed for every tracked asset or industry; AI context depends on eligible recent evidence and provider availability. Historical news/AI and a complete archived-day experience remain post-MVP (#15/#16). Further enhancements are tracked in [#30](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/30) (per-industry news status), [#31](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/31) (automatic redisplay after refollow), and [#32](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/32) (provider-wide asset discovery).

M4 evidence: [#20](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/20) records the initial automated-suite verification (119 backend tests and 45 frontend tests, plus frontend build; original Windows rerun was blocked by an environment-level Python issue). [#21](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/21) records the separately runnable integration suite (4 passed), a subsequent backend suite (123 passed), and frontend/build checks. Later targeted QA for [#29](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/29) passed the weekend-quote fix; that issue also records a date-dependent full-suite AI-context test failure, so these are historical test snapshots, **not a claim that the latest full suite was rerun for #23**. The human accepted the local MVP in [#22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22).

The project owner reports manually checking the hosted application's persistence, deployment workflow, and rollback. Review and explicitly prioritize post-MVP issues #15/#16 and #30–#32 remains future work.

## Run with Docker Compose

With Docker Desktop (including Compose) installed, start the app and PostgreSQL from the repository root:

```powershell
Copy-Item .env.compose.example .env.compose
# Edit .env.compose and replace the example local database password.
docker compose --env-file .env.compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Compose waits for PostgreSQL readiness, and the app applies Alembic migrations before starting. The `postgres_data` volume keeps the watchlist, purchase lots, and other stored data across app restarts. Stop with `Ctrl+C`, then run `docker compose --env-file .env.compose down`; this preserves the database volume. To remove the stored database as well, run `docker compose --env-file .env.compose down --volumes`.

The example environment file contains only local database and port settings. Market/news refresh and AI context need optional `EODHD_API_KEY`, `MARKETAUX_API_KEY`, and `OPENAI_API_KEY` values supplied by you in `.env.compose`; they are not required to start the application and no provider credentials are included in the image. `MARKETLENS_PORT` changes the host port (the app remains on container port 8000).

### Local dashboard observability demo (issue #38)

The optional LGTM stack instruments only the stored `GET /api/dashboard` journey. The React request creates a W3C `traceparent`; FastAPI extracts it and creates the server span, then a repository-boundary span covers the PostgreSQL read. Request count, latency, and a structured request log carry the same trace ID. Other routes and the normal Compose/Render deployment remain uninstrumented. The app exports to the local collector over gRPC by default, or directly to a configured OTLP endpoint over HTTP/protobuf.

Telemetry is deliberately limited to service/environment, route template, method, status, duration, outcome, exception class, and trace/span IDs. It does not record headers, query strings, SQL text or parameters, exception messages, request/response bodies, asset or article identifiers, holdings, quantities, or values. The isolated local stack stores telemetry in local Docker volumes with 24-hour retention for traces, logs, and metrics; Grafana uses the local demo login `admin` / `admin`. By default no telemetry is sent outside the local stack. Direct Grafana Cloud export is enabled only when explicitly configured in the deployed service environment.

With Docker Compose installed, run these commands in PowerShell from the repository root:

```powershell
Copy-Item .env.observability.example .env.observability
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

### Local dashboard availability alert (issue #39)

The local Grafana rule `Dashboard unavailable` evaluates every 10 seconds and fires when at least one dashboard HTTP 5xx is observed in the rolling previous minute. It resolves after a full minute without a dashboard failure. Alert math uses a dedicated low-cardinality failure counter because the trace-correlated request counter has one unique trace ID per series and cannot produce a meaningful rolling increase. The local demo exports metrics every 5 seconds for a responsive demonstration. Grafana sends firing and resolved notifications to an internal-only webhook in the isolated Compose network. The receiver retains only the alert state, static rule name/severity/journey, a validated trace ID if a future rule supplies one, and the Grafana fingerprint/start time; repeated deliveries for the same alert transition are idempotent. It drops annotations, URLs, arbitrary labels, request data, and credentials. Its webhook contract is a local hand-off surface that a later on-call responder can consume.

Start or rebuild the optional stack using the #38 commands above. Reproduce and recover without contacting external providers:

```powershell
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml stop db
curl.exe -i http://localhost:8001/api/dashboard
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml logs --since 2m alert-receiver
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml start db
curl.exe -i http://localhost:8001/api/dashboard
```

The stopped database produces HTTP 500; the alert receiver logs one redacted `firing` event. After PostgreSQL is healthy, the dashboard returns HTTP 200 and Grafana delivers `resolved` after the failure leaves the one-minute window. In Grafana **Alerting → Alert rules**, verify `Dashboard unavailable` returns to **Normal**. The delivery contains the alert fingerprint and static journey/route/status class. To find the corresponding trace, open Loki in Explore and query `{service_name="marketlens-api"} |= "dashboard_request"`; select the matching time and use its configured trace link to Tempo. The alert threshold, delivery and recovery tests are in `tests/test_alert_receiver.py`. Do not stop a database outside this isolated observability project.

Redacted local run evidence (same fingerprint for firing and recovery; repeated webhook posts produced no duplicate `alert_delivery` record):

```text
2026-10-25T19:35:15Z alert_delivery {"fingerprint":"0850647b23910719","labels":{"alert_id":"dashboard-availability","alertname":"Dashboard unavailable","http_request_method":"GET","http_response_status_class":"5xx","http_route":"/api/dashboard","journey":"dashboard","journey_outcome":"failure","severity":"critical"},"startsAt":"2026-10-25T19:34:40Z","status":"firing"}
2026-10-25T19:35:45Z alert_delivery {"fingerprint":"0850647b23910719","labels":{"alert_id":"dashboard-availability","alertname":"Dashboard unavailable","http_request_method":"GET","http_response_status_class":"5xx","http_route":"/api/dashboard","journey":"dashboard","journey_outcome":"failure","severity":"critical"},"startsAt":"2026-10-25T19:34:40Z","status":"resolved"}
```

#### Production alert in Grafana Cloud

The local alert above remains the safe fault-injection demo. For production, reuse the owner-managed Synthetic Monitoring check `marketlens-production-dashboard`; do not create a duplicate. The check should remain a public HTTP `GET` to `https://marketlens-dtc.onrender.com/api/dashboard`, accept only HTTP 200, run every 5 minutes from one European probe, and use a 60-second timeout. Render Free services can sleep after 15 minutes idle and take about one minute to wake, so a single timed-out probe is expected to be transient; the timeout plus the repeated-failure threshold below prevents one cold start from paging. Keep the existing frequency and probe count to avoid extra check executions.

In Grafana Cloud, open **Testing & synthetics → Synthetics → Checks**, edit the existing check, confirm its target/method/status/frequency/probe, set **Timeout** to 60 seconds, and save. Verify the `job` label is `marketlens-production-dashboard` and `instance` is the API URL in **Explore → Metrics** with `probe_success`. Grafana's Synthetic Monitoring labels use the configured job name as `job`, the target as `instance`, and the location as `probe` ([check metrics and labels](https://grafana.com/docs/grafana-cloud/observe-and-act/testing/synthetic-monitoring/create-checks/checks/)).

Create one **Grafana-managed** alert rule in the existing Grafana Cloud stack using its Prometheus/Mimir data source. Call it `MarketLensProductionDashboardUnavailable`; evaluate every **1 minute**, set the pending period to **1 minute**, and alert when query A is **above 0.5**. This query counts actual failed probe samples in a rolling 15-minute window (a success is 1, a failure is 0) and returns 0 while healthy, so a single Render cold-start miss does not fire:

```promql
(
  sum by (job, instance, probe) (
    count_over_time(probe_success{
      job="marketlens-production-dashboard",
      instance="https://marketlens-dtc.onrender.com/api/dashboard"
    }[15m])
    -
    sum_over_time(probe_success{
      job="marketlens-production-dashboard",
      instance="https://marketlens-dtc.onrender.com/api/dashboard"
    }[15m])
  )
) >= bool 2
```

If the `job` label in your check differs, use the exact value shown by `probe_success`; keep the URL filter exact. Add these rule labels: `service=marketlens`, `environment=production`, `source=synthetic`, and `severity=critical`. Set the summary annotation to `MarketLens production dashboard API is unavailable` and the description to `Synthetic check {{ $labels.job }} for {{ $labels.instance }} at probe {{ $labels.probe }} recorded at least 2 failures in 15m. Check its recent results in Synthetic Monitoring.` Do not include response bodies or other request data. Set **No data** and **Error** handling to **Keep last state**: probe failures are reported as `probe_success=0`, while missing check telemetry is a monitoring-pipeline issue to inspect separately. The rule resolves once fewer than two failed samples remain in the rolling window and the pending period clears.

For email delivery, go to **Alerts & IRM → Alerting → Notification configuration → Contact points** and create an **Email** contact point for your own address. Test it there. Then create a child notification policy matching `service=marketlens`, `environment=production`, and `source=synthetic`; select that email contact point, keep resolved notifications enabled, group by `alertname`, `job`, and `instance`, set group wait to **30 seconds**, group interval to **5 minutes**, and repeat interval to **4 hours**. Keep these labels stable so a future owner-managed webhook route can be added without changing the alert rule. Grafana Cloud provides email delivery without a self-managed SMTP server ([contact points](https://grafana.com/docs/grafana-cloud/alerting-and-irm/alerting/configure-notifications/manage-contact-points/), [email integration](https://grafana.com/docs/grafana-cloud/alerting-and-irm/alerting/configure-notifications/manage-contact-points/integrations/configure-email/), [notification policies](https://grafana.com/docs/grafana-cloud/observe-and-act/alert-and-measure-reliability/alerting/configure-notifications/create-notification-policy/)).

Validate without taking production down: (1) confirm the existing check is enabled and its latest result is green/HTTP 200; (2) send Grafana's test notification from the email contact point and confirm receipt; (3) create a temporary, clearly named `MarketLensNotificationRouteTest` rule using the same notification labels, PromQL `vector(1)`, and a condition above 0.5; confirm a firing email; change it to `vector(0)`, confirm a resolved email, then delete the temporary rule. This tests notification routing only; it is simulated evidence, not a real production outage. The real production threshold is passively verified from the existing check with `probe_success{job="marketlens-production-dashboard",instance="https://marketlens-dtc.onrender.com/api/dashboard"}`: healthy is 1; repeated check failure is 0. Render Free can take about one minute to wake ([Render Free services](https://render.com/docs/free)); do not inject a failure into Render or Neon. Grafana Cloud account configuration and email receipt must be verified by the owner; Codex has no account access.

### Local on-call recovery demo (issue #40)

This reuses only the optional `marketlens-observability` Compose stack. Keep the host agent running before fault injection so it detects the real Grafana event automatically. The receiver feed is published on loopback only (`127.0.0.1:8081`); it exposes sanitized alert events, never a command endpoint.

In terminal 1, start the isolated stack as above and run the host agent from the repository root:

```powershell
uv run python -m app.oncall_agent
```

Wait for `oncall status=ready`. In terminal 2, create the approved isolated fault and inspect the dashboard:

```powershell
docker compose --project-name marketlens-observability --env-file .env.observability -f compose.observability.yaml stop db
curl.exe -i http://127.0.0.1:8001/api/dashboard
```

Grafana's real dashboard availability notification reaches the receiver; the agent reads the sanitized event feed, verifies the fixed project/service labels and that the DB is stopped or running unhealthy, then runs the same single action in either case: `docker compose ... restart db`. Compose restart was verified to start the stopped isolated DB. The agent checks the DB health and polls `/api/dashboard` for HTTP 200 before logging `oncall status=recovered`. Grafana later sends `resolved`; the agent rechecks the dashboard before logging `resolved_verified`. Keep the agent process running through recovery and resolution. The agent writes only the validated alert fingerprint, start time, and state (`attempted`, `recovered`, or `resolved`) to an atomically replaced, gitignored `.oncall-agent-state.json` file. On restart, replayed firing alerts escalate without another action; resolved alerts are acknowledged only when a prior recovery was recorded and the dashboard is currently healthy. Missing/corrupt state, unknown alerts, a healthy DB, duplicate events, or failed verification produce an escalation with no retry. It does not connect to Render or providers, accept shell input, or access any other Compose project. Audit output contains only allowlisted status/action values and no request or database payloads.

The receiver's GET `/agent/events?after=N` endpoint is read-only and returns only its redacted delivery registry. The first repeated firing delivery adds one redacted `repeated` feed event; the poller explicitly escalates it as `oncall status=escalated reason=repeated_alert` without taking a second action. Further repeats of that same firing are coalesced. Tests cover the single fixed-target restart for stopped and unhealthy states, durable replay across agent restarts, end-to-end receiver/feed/poller wake-up, unexpected labels, already-healthy state, repeated alerts, and failed health/dashboard verification. The real end-to-end chain requires Docker and the optional local observability stack; verify the firing and resolved `oncall` records in the terminal and the alert state under Grafana **Alerting → Alert rules**. Never stop a database outside this isolated project.

Redacted automatic recovery evidence (2026-10-25 UTC; one allowed `restart db`, no duplicate action):

```text
20:08:40Z  dashboard fault injected only by stopping marketlens-observability/db; /api/dashboard returned HTTP 500
20:09:14Z  alert_delivery status=firing fingerprint=0850647b23910719
20:09:24Z  oncall status=recovered action=restart dashboard=healthy; marketlens-observability/db healthy; /api/dashboard returned HTTP 200
20:09:44Z  alert_delivery status=resolved fingerprint=0850647b23910719
20:09:46Z  oncall status=resolved_verified
```

### Hosted Cloudflare on-call responder (issue #40)

The hosted production responder is a separate Python Worker and SQLite-backed Durable Object under `hosted_oncall/`. It does not replace or change the local receiver, poller, Docker action, or local fault-injection workflow above. It accepts only the `MarketLensProductionDashboardUnavailable` alert with the production labels and exact dashboard URL; Grafana HMAC-SHA256 plus a timestamp (maximum age five minutes) protects the webhook. The Durable Object records each alert and audit transition before acknowledging it. A fingerprint/start-time replay cannot repeat the action, and the restart boundary is saved before the Render API request. State or API uncertainty fails closed.

The agent first checks `GET /api/dashboard` and observes `GET /health/ready`. If the dashboard is already healthy, it takes no action. After any initial dashboard 5xx it waits the full 70-second Render Free cold-start grace before classifying readiness, then checks both endpoints again. This lets a transient initial readiness 503 or unknown response recover during startup; only post-grace observations decide whether to proceed. A healthy dashboard and readiness 200 end the incident without restart. Persistent readiness 503, unknown readiness, dashboard probe errors, and non-5xx dashboard responses escalate without restart. For a persistent dashboard 5xx, the agent additionally requires post-grace database readiness 200 and the configured active Render Web Service with its latest deploy `live`. In-progress deployments, suspended services, and unverified Render state escalate without restart. Only then can the single fixed `POST /v1/services/{RENDER_SERVICE_ID}/restart` operation run. Afterward it checks database readiness and the public dashboard for up to 90 seconds; only HTTP 200 with the expected dashboard JSON shape is recorded as recovered. It never reads or acts on Grafana annotations or alert-supplied URLs/commands.

#### Owner deployment steps

1. Confirm issue #39's production rule is active and the existing email notification still fires. Install a current `uv` version (**0.13.4 or later**) and Node.js locally. From the repository root, run:

   ```powershell
   Set-Location hosted_oncall
   uv sync
   uv run pywrangler dev
   ```

2. In the Render Dashboard, open the deployed MarketLens Web Service and copy its immutable service ID from the service details/URL. Create an API key in Render Account Settings. Render API keys apply to all workspaces the account belongs to; review that scope before creating the key. The code always uses the one configured service ID and the one restart endpoint. Never paste either secret into chat or commit it.

3. In the Cloudflare dashboard, sign in with `uv run pywrangler login`. From `hosted_oncall/`, add the two secrets through the CLI prompts (the values are entered locally and are not part of this repository):

   ```powershell
   uv run pywrangler secret put GRAFANA_HMAC_SECRET
   uv run pywrangler secret put RENDER_API_KEY
   ```

   The Grafana HMAC secret must be at least 32 characters. Deploy with the configured service ID and public dashboard URL as non-secret Worker vars:

   ```powershell
   uv run pywrangler deploy `
     --var "RENDER_SERVICE_ID:srv-<service-id>" `
     --var "MARKETLENS_DASHBOARD_URL:https://marketlens-dtc.onrender.com/api/dashboard"
   ```

   `wrangler.toml` provisions the `Incidents` Durable Object using SQLite on first deploy. Do not remove its migration or change the Durable Object class name after deployment; that could create new state and weaken replay protection. Cloudflare's current Free limits include 100,000 Worker requests/day; Durable Objects Free also has daily request and compute quotas (100,000 requests and 13,000 GB-s/day). These quotas reset daily and operations can fail when exhausted; Free has no production availability SLA. If the Worker or Durable Object is unavailable, it does not restart Render and Grafana email remains the escalation path ([Workers limits](https://developers.cloudflare.com/workers/platform/limits/), [Durable Objects pricing](https://developers.cloudflare.com/durable-objects/platform/pricing/)).

4. In Grafana Cloud, add an authenticated **Webhook** integration to the existing production email contact point (or a matching webhook notification route while leaving the email route active). Set its URL to `https://<your-worker-domain>/webhook`. Enable HMAC-SHA256 with the same locally held `GRAFANA_HMAC_SECRET`, signature header `X-Grafana-Alerting-Signature`, and timestamp header `X-Grafana-Alerting-Timestamp`. Do not put secrets in the URL. Preserve the rule labels `service=marketlens`, `environment=production`, `source=synthetic`, `severity=critical`, `job=marketlens-production-dashboard`, and `instance=https://marketlens-dtc.onrender.com/api/dashboard`.

5. First use Grafana's contact-point test to verify the endpoint/authentication; a generic test payload is acknowledged but ignored by the strict alert validator. To verify the full safe path without disrupting production, briefly create a test alert with the exact production alert name/labels and a constant firing expression while MarketLens is healthy. Confirm the signed webhook appears in the Worker tail and that the incident is recorded as `no_action` because the dashboard returns 200. Resolve/delete the test rule, confirm the resolved delivery, and confirm the email integration remains active. Do **not** simulate a production outage or use a Render restart in production as a test.

6. Read redacted live diagnostics with `uv run pywrangler tail`. Worker logs contain only status/reason; the Durable Object stores the incident key, transition, safe reason, and timestamp, not payload text, API responses, or credentials. To verify the application readiness endpoint without revealing database details, request `GET https://marketlens-dtc.onrender.com/health/ready`; it returns 200 for `SELECT 1` success and an empty 503 otherwise.

Required Worker configuration names (values are owner-entered): `GRAFANA_HMAC_SECRET`, `RENDER_API_KEY`, `RENDER_SERVICE_ID`, and `MARKETLENS_DASHBOARD_URL`. The two secrets belong in Cloudflare secret settings; the service ID and dashboard URL are non-secret Worker vars. Tests use mocked Grafana requests, SQLite storage, Render responses, and dashboard behavior. Actual Cloudflare deployment, Grafana delivery/authentication, and production restart verification remain owner-side steps and are not evidenced by local tests.

### Render deployment

The live application is [https://marketlens-dtc.onrender.com/](https://marketlens-dtc.onrender.com/). Its repository settings are:

- **Service type:** Web Service
- **Runtime:** Docker
- **Branch:** `main`
- **Auto-deploy:** After CI checks pass
- **Root directory:** repository root (leave blank)
- **Dockerfile path:** `./Dockerfile`
- **Docker build context:** repository root (`.`)
- **Port:** use Render's injected `PORT`; the image defaults to `8000` for local runs. Do not set `PORT` manually in Render.

The Docker startup command runs `alembic upgrade head` before starting Uvicorn. For deployment, provide a Neon PostgreSQL connection string in the required `DATABASE_URL` environment variable and retain its `sslmode=require` option. The app accepts Neon `postgres://` and `postgresql://` URL schemes and adapts them to the installed `psycopg` driver.

Configure these environment variables in the Render service:

- **Required:** `DATABASE_URL`
- **Optional provider features:** `EODHD_API_KEY` (market prices), `MARKETAUX_API_KEY` (news), and `OPENAI_API_KEY` (AI context). `MARKETAUX_USER_AGENT` and `OPENAI_MODEL` can override their application defaults.
- **Separate frontend only:** `CORS_ALLOWED_ORIGINS`, set to the exact frontend origin if it is hosted on a different origin. The current app serves its frontend and API from the same service.

The project owner reports manually verifying deployment through CI/CD, saved watchlist data across a restart, and a Render dashboard rollback. This documentation update did not independently exercise the live service. To check it, open the URL above, confirm the page title is “MarketLens | Market context,” add a watchlist asset, then revisit it after a service restart. GitHub Actions checks backend tests, frontend tests, and the production frontend build on pull requests and pushes to `main`.

To roll back, open the service's **Deploys** page in the [Render Dashboard](https://dashboard.render.com/), choose a previous successful deploy, and select **Rollback**. A dashboard rollback disables automatic deploys; re-enable them from the service **Settings** page when ready. A code rollback does not roll back Neon schema migrations or database data, so confirm the selected application version is compatible with the current database schema. See [Render's rollback guide](https://render.com/docs/rollbacks).

For local Compose persistence checks, add an asset to the watchlist and, if marking it Owned, save purchase lots. Stop and restart with the Compose commands above, then confirm the asset and lots remain. `docker compose --env-file .env.compose logs app` shows startup and migration output. This local setup does not publish the app to the internet.

## Deployment and CI/CD

GitHub Actions runs the backend unit and integration suite, frontend tests, and production build on pull requests and pushes to `main`. Locally, run `uv sync && uv run pytest` for the backend and integration tests, then `npm ci --prefix frontend && npm --prefix frontend run test && npm --prefix frontend run build` for the frontend checks. These automated checks use local test data and do not require provider API keys.

### AI context (issue #13)

Set optional `OPENAI_API_KEY` in the ignored backend `.env`; `OPENAI_MODEL` defaults to `gpt-6-luna` with low reasoning effort. Apply the additive Alembic migration before running the feature. No new Python or frontend packages are required.

Only manual refresh triggers AI, after prices and news have been committed. AI reads stored metadata and current movements (recent 72-hour evidence); it never requests extra market/news data. Each user has a persistent one-hour cooldown, at most two AI calls per eligible refresh, at most five ambiguous articles, five tracked assets, twelve classified articles (three per asset), 500 snippet characters per article, 1,200 output tokens per call, a 12-second timeout, and no automatic retries. Missing credentials, invalid output and quota failures leave successful market/news refresh intact. Unclassified/Not Relevant candidates remain hidden from the feed. Summaries are reused across restarts when evidence is unchanged and replaced per asset only after valid changed output.

The LLM selects classifications with verified source quotations and persisted article IDs. It selects up to two relevant reports per summary; the service renders a short qualified card using only the stored exact price/movement and selected report counts/categories. Article headline/snippet prose is never quoted or paraphrased into the summary body; original metadata remains attributed in the linked news feed. This constrained rendering keeps advice, causal claims, targets, fabricated sources and unsupported confidence scores out of summary bodies without relying on a text blacklist. The persistent UI disclaimer still applies; source relevance is uncertain and the bounded evidence window may omit useful context.

Optional live smoke check (not automated; incurs your own API usage): configure your key/model and use a disposable local database with a current tracked-asset price/movement and one persisted source-linked relevant article. Invoke `ContextService(ContextRepository(session), OpenAIProvider()).refresh(demo_user_id)` once from a backend Python session. This checks AI against stored evidence without new market/news calls. Then read `GET /api/dashboard` and verify one qualified card, the actual publisher link, movement, and exact uncertainty disclaimer. Repeat dashboard reads and the service call within the cooldown; they should reuse the stored card. Do not reset/delete the cooldown or retry unavailable output repeatedly. Automated tests fake all AI HTTP responses and use isolated databases; no live OpenAI check was run for this implementation.
