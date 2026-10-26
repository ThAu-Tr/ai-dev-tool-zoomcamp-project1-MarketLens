# MarketLens

**MarketLens** is a lightweight investment-monitoring dashboard for everyday investors. It brings together tracked stocks, ETFs and indices, price history, relevant news, and qualified AI-generated market context. It is an educational monitoring tool, **not** a trading platform or source of investment advice.

**[Open the live application](https://marketlens-dtc.onrender.com/)** · **[Project issues](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues)** · **[Development workflow](_docs/process.md)** · **[AI-assisted development evidence](_docs/ai-usage-report.md)**

> **Project status (October 2026):** The locally accepted MVP is deployed publicly on Render. Production dashboard observability and Grafana Cloud monitoring are documented below. The local on-call demonstration has independent QA evidence; the separate hosted Cloudflare responder is still undergoing deployment/acceptance debugging under [issue #40](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/40). Do not treat hosted recovery as verified.

## Reviewer quick links

| What to review | Where |
| --- | --- |
| Live demo | [MarketLens on Render](https://marketlens-dtc.onrender.com/) |
| Local startup | [Quick start with Docker Compose](#quick-start-with-docker-compose) |
| Tests and CI/CD | [Running checks](#running-checks) · [GitHub Actions](.github/workflows) |
| Architecture and API | [Architecture](#architecture) · [OpenAPI contract](openapi.yaml) |
| AI-assisted engineering | [Development process](_docs/process.md) · [Agent instructions](AGENTS.md) · [AI usage report](_docs/ai-usage-report.md) |
| Observability, alerts and recovery | [Local observability](#local-dashboard-observability-demo-issue-38) · [Grafana Cloud](#grafana-cloud-export-for-the-deployed-dashboard) · [On-call demo](#local-on-call-recovery-demo-issue-40) |
| Scope and limitations | [MVP scope](#mvp-scope) · [Limitations](#limitations-and-future-work) |

## Quick start with Docker Compose

**Prerequisites:** Git and Docker Desktop with Docker Compose. From the repository root, use PowerShell (copy the example files only on first setup; do not overwrite existing local files containing credentials):

```powershell
Copy-Item .env.example .env
Copy-Item .env.compose.example .env.compose
# Set provider keys in .env (optional for startup; needed for refresh).
# Replace the sample local database password in .env.compose.
# Docker creates its own DATABASE_URL; leave DATABASE_URL in .env empty.
docker compose --env-file .env --env-file .env.compose up --build
```

Open **http://localhost:8000**. Compose starts the application and PostgreSQL and applies Alembic migrations on startup. Market-data, news and AI refreshes require your own optional API keys; the application itself can start without them. The latter file takes precedence for overlapping Compose settings. `DATABASE_URL` in `.env` is ignored by the Docker app because `compose.yaml` explicitly constructs its PostgreSQL connection URL using the `db` service. Stop with `Ctrl+C` and `docker compose --env-file .env --env-file .env.compose down` (keeps the database volume). See [Run with Docker Compose](#run-with-docker-compose) for persistence, options and troubleshooting context.

## The problem

Everyday investors often need to piece together price movements, company news, industry developments, and wider events from separate sources. That makes it difficult to understand what may be relevant today or to revisit the context around a past market day.

MarketLens brings those inputs into a combined dashboard and a persistent historical price timeline. It is a monitoring and context tool—not a trading system, portfolio optimiser, or source of investment recommendations.

## What exists today

The locally accepted MVP includes a persisted dashboard; a bounded, curated stock/ETF/index catalogue; Owned and Interested watchlists with purchase lots; followed industries; manual refresh of prices through EODHD and categorized news through Marketaux; qualified, source-linked AI context; and a historical price timeline.

The asset picker searches a local catalogue rather than the provider's entire supported universe. Provider-wide discovery is deferred to [#32](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/32). News per followed industry and automatic redisplay of stored news after refollowing are deferred to [#30](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/30) and [#31](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/31). Human acceptance and the history of corrected defects are recorded in [#22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22).

### AI context (issue #13)

MarketLens optionally generates qualified, source-linked AI context using stored market movements and news after a manual refresh. The feature is bounded by rate limits and evidence constraints; missing credentials or AI failures do not prevent prices and news from refreshing. See [AI context implementation and validation](_docs/guides/ai-context.md) for configuration, safeguards, and testing.

## Demo

Try the [live MarketLens application](https://marketlens-dtc.onrender.com/). On Render Free, the first request after inactivity may take longer while the service wakes up. A screenshot or video walkthrough has not yet been added; the public app is the primary demo.

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

## AI-assisted development and review evidence

MarketLens was developed through GitHub issues with an AI-assisted Engineer → independent QA workflow. The orchestrator coordinates work, QA reports PASS/FAIL against issue acceptance criteria, and **only the human owner closes an issue after manual acceptance**. This makes implementation decisions, corrections and acceptance evidence reviewable.

- [Agent instructions](AGENTS.md) and [development process](_docs/process.md)
- [AI-assisted workflow evidence](_docs/ai-usage-report.md)
- [Architecture decisions](_docs/architecture.md), [product specification](_docs/plan.md), and [backlog](_docs/backlog.md)
- [GitHub issue history](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues) and [GitHub Actions checks](.github/workflows)

The hosted production on-call extension is tracked separately in [#40](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/40); local acceptance and production acceptance are not interchangeable.

## Running checks

GitHub Actions runs backend unit/integration tests, frontend tests, and the frontend production build. The integration suite uses isolated SQLite and mocked providers; it does not establish live provider or PostgreSQL compatibility. See [testing and verification](_docs/guides/testing.md#automated-checks-and-test-coverage) for commands, coverage, and limitations.

## Local development and configuration

For the recommended reviewer setup, use [Docker Compose](#quick-start-with-docker-compose). For manual development, copy `.env.example` to the ignored `.env`, provide a PostgreSQL `DATABASE_URL`, run `uv run alembic upgrade head`, and start FastAPI with `uv run uvicorn app.main:app --reload`. In another terminal, run `npm ci --prefix frontend` and `npm --prefix frontend run dev`. The frontend reads `VITE_API_BASE_URL` (set it to `http://127.0.0.1:8000` when needed); set `CORS_ALLOWED_ORIGINS` for the development frontend origin. Never expose provider API keys in the frontend.

The manual PostgreSQL provisioning and clean-checkout development startup have not been independently verified. The Docker quick start is the recommended approach.

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

With Docker Desktop (including Compose) installed, start the app and PostgreSQL from the repository root. Copy both examples **only if the destination files do not already exist**, to avoid overwriting your own settings or secrets:

```powershell
Copy-Item .env.example .env
Copy-Item .env.compose.example .env.compose
# Put your EODHD, Marketaux and OpenAI keys in .env if you want refresh features.
# Edit .env.compose and replace the example local database password.
docker compose --env-file .env --env-file .env.compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Compose waits for PostgreSQL readiness, and the app applies Alembic migrations before starting. The `postgres_data` volume keeps the watchlist, purchase lots, and other stored data across app restarts. Stop with `Ctrl+C`, then run `docker compose --env-file .env --env-file .env.compose down`; this preserves the database volume. To remove the stored database as well, run `docker compose --env-file .env --env-file .env.compose down --volumes`.

The default setup uses **both** gitignored environment files: `.env` (optional `EODHD_API_KEY`, `MARKETAUX_API_KEY` and `OPENAI_API_KEY` for market/news/AI refresh) and `.env.compose` (local PostgreSQL credentials and `MARKETLENS_PORT`). The command lists `.env` first and `.env.compose` last so Compose-specific database and port settings take precedence. `DATABASE_URL` may be blank in `.env`: `compose.yaml` explicitly creates the container's database URL using the PostgreSQL `db` service, so it does not use the host/Neon URL from `.env`. With blank provider keys, the app starts but provider-dependent refreshes cannot complete. Do not commit secrets; no provider credentials are bundled in the image or repository. `MARKETLENS_PORT` changes the host port (the app remains on container port 8000).

## Observability and operations

Operational monitoring and recovery are documented in separate runbooks; the following summaries describe how to find them.

### Local dashboard observability demo (issue #38)

The separate `compose.observability.yaml` stack runs an isolated application at `http://localhost:8001` and Grafana at `http://localhost:3000`. Copy `.env.observability.example` to `.env.observability` on first setup; replace its example database password. Provider API keys are optional for the monitoring/on-call demo (add them only for live refresh features). The regular Docker application remains on port `8000`. The receiver feed is loopback-only on `127.0.0.1:8081`, and Prometheus uses `9090`.

**Full setup, environment notes, metrics, traces, and fault-injection guide:** [Observability runbook](_docs/guides/observability.md#local-dashboard-observability-demo-issue-38).

### Grafana Cloud export for the deployed dashboard

The deployed dashboard can export scoped OpenTelemetry signals to Grafana Cloud using Render environment configuration. This is separate from the local LGTM demo.

**Full setup and troubleshooting:** [Observability runbook](_docs/guides/observability.md#grafana-cloud-export-for-the-deployed-dashboard).

### Local dashboard availability alert (issue #39)

Grafana monitors dashboard availability and provides a controlled way to demonstrate user-impact alerting in the isolated local environment; the production Grafana Cloud alert is documented separately.

**Alert rules, notifications, safe tests, and evidence:** [Alerting runbook](_docs/guides/alerting.md#local-dashboard-availability-alert-issue-39).

### Local on-call recovery demo (issue #40)

An alert from the isolated Grafana stack can wake a locally running host agent that performs a bounded Docker database restart and verifies the dashboard recovered. The **hosted Cloudflare responder remains unverified** and is not part of the accepted local demonstration.

**Agent startup, allowed actions, recovery test, and limitations:** [On-call agent runbook](_docs/guides/oncall-agent.md#local-on-call-recovery-demo-issue-40).

## Deployment and CI/CD

GitHub Actions runs the backend unit and integration suite, frontend tests, and production build on pull requests and pushes to `main`. Locally, run `uv sync && uv run pytest` for the backend and integration tests, then `npm ci --prefix frontend && npm --prefix frontend run test && npm --prefix frontend run build` for the frontend checks. These automated checks use local test data and do not require provider API keys.

### Render deployment

MarketLens is deployed on [Render](https://marketlens-dtc.onrender.com/) from `main` with Docker and Neon PostgreSQL. For required environment variables, production configuration, rollback, and persistence validation, see the [deployment runbook](_docs/guides/deployment.md#render-deployment).
