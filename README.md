# MarketLens

MarketLens is a lightweight investment-monitoring application for everyday investors who want to follow stocks, ETFs, and major indices in one place. It combines price movement with relevant news and carefully qualified AI context so users can understand possible market context without receiving investment advice.

> **Project status:** M4 local MVP accepted ([human acceptance #22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22)); milestone documentation is tracked in [#23](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/23). M5 (containerization, CI/CD, deployment) comes next.

## The problem

Everyday investors often need to piece together price movements, company news, industry developments, and wider events from separate sources. That makes it difficult to understand what may be relevant today or to revisit the context around a past market day.

MarketLens brings those inputs into a combined dashboard and a persistent historical price timeline. It is a monitoring and context tool—not a trading system, portfolio optimiser, or source of investment recommendations.

## What exists today

The locally accepted MVP includes a persisted dashboard; a bounded, curated stock/ETF/index catalogue; Owned and Interested watchlists with purchase lots; followed industries; manual refresh of prices through EODHD and categorized news through Marketaux; qualified, source-linked AI context; and a historical price timeline.

The asset picker searches a local catalogue rather than the provider's entire supported universe. Provider-wide discovery is deferred to [#32](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/32). News per followed industry and automatic redisplay of stored news after refollowing are deferred to [#30](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/30) and [#31](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/31). Human acceptance and the history of corrected defects are recorded in [#22](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/22).

## Demo

There is no deployed demo, video, or screenshot yet.

// TODO (M5/M8): Create and link actual MarketLens demo screenshots or a short recording. No demo artifact exists yet; do not mark this complete until it can be opened and reviewed.

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

// TODO (M5/M8): After deployment, record limitations actually observed in the hosted application (availability, data/provider quotas, persistence, and hosting constraints as applicable); review and explicitly prioritize post-MVP issues #15/#16 and #30–#32. Current local-MVP limitations and links are documented, but deployment evidence and post-MVP ordering are not.

## Run with Docker Compose

With Docker Desktop (including Compose) installed, start the app and PostgreSQL from the repository root:

```powershell
Copy-Item .env.compose.example .env.compose
# Edit .env.compose and replace the example local database password.
docker compose --env-file .env.compose up --build
```

Open [http://localhost:8000](http://localhost:8000). Compose waits for PostgreSQL readiness, and the app applies Alembic migrations before starting. The `postgres_data` volume keeps the watchlist, purchase lots, and other stored data across app restarts. Stop with `Ctrl+C`, then run `docker compose --env-file .env.compose down`; this preserves the database volume. To remove the stored database as well, run `docker compose --env-file .env.compose down --volumes`.

The example environment file contains only local database and port settings. Market/news refresh and AI context need optional `EODHD_API_KEY`, `MARKETAUX_API_KEY`, and `OPENAI_API_KEY` values supplied by you in `.env.compose`; they are not required to start the application and no provider credentials are included in the image. `MARKETLENS_PORT` changes the host port (the app remains on container port 8000).

### Render deployment

Create a **Web Service** from this repository and select **Docker** as the runtime. Leave the Dockerfile path as `./Dockerfile` and the Docker build context as the repository root. Render supplies `PORT`; the container listens on that value (and uses `8000` when it is absent). The container applies `alembic upgrade head` before starting the web server.

Create a Neon PostgreSQL database and set the web service's `DATABASE_URL` environment variable to its connection string. Both `postgres://` and `postgresql://` URLs are adapted to the installed `psycopg` driver; keep Neon’s `sslmode=require` query parameter. Add `CORS_ALLOWED_ORIGINS` with the exact deployed frontend origin if the frontend is hosted separately. Provider keys are optional for starting the service: `EODHD_API_KEY`, `MARKETAUX_API_KEY`, and `OPENAI_API_KEY`.

For a persistence check, add an asset to the watchlist and, if marking it Owned, save one or more purchase lots. Stop and restart with the commands above, then confirm the asset and lots remain. `docker compose --env-file .env.compose logs app` shows startup and migration output. This local container setup does not publish the app to the internet.

## Deployment and CI/CD

GitHub Actions runs the backend unit and integration suite, frontend tests, and production build on pull requests and pushes to `main`. Locally, run `uv sync && uv run pytest` for the backend and integration tests, then `npm ci --prefix frontend && npm --prefix frontend run test && npm --prefix frontend run build` for the frontend checks. These automated checks use local test data and do not require provider API keys.

// TODO (M5): After implementing and verifying deployment, document actual hosting, deployment workflow, and the working public application URL. None is yet implemented or verified in this README.


### AI context (issue #13)

Set optional `OPENAI_API_KEY` in the ignored backend `.env`; `OPENAI_MODEL` defaults to `gpt-6-luna` with low reasoning effort. Apply the additive Alembic migration before running the feature. No new Python or frontend packages are required.

Only manual refresh triggers AI, after prices and news have been committed. AI reads stored metadata and current movements (recent 72-hour evidence); it never requests extra market/news data. Each user has a persistent one-hour cooldown, at most two AI calls per eligible refresh, at most five ambiguous articles, five tracked assets, twelve classified articles (three per asset), 500 snippet characters per article, 1,200 output tokens per call, a 12-second timeout, and no automatic retries. Missing credentials, invalid output and quota failures leave successful market/news refresh intact. Unclassified/Not Relevant candidates remain hidden from the feed. Summaries are reused across restarts when evidence is unchanged and replaced per asset only after valid changed output.

The LLM selects classifications with verified source quotations and persisted article IDs. It selects up to two relevant reports per summary; the service renders a short qualified card using only the stored exact price/movement and selected report counts/categories. Article headline/snippet prose is never quoted or paraphrased into the summary body; original metadata remains attributed in the linked news feed. This constrained rendering keeps advice, causal claims, targets, fabricated sources and unsupported confidence scores out of summary bodies without relying on a text blacklist. The persistent UI disclaimer still applies; source relevance is uncertain and the bounded evidence window may omit useful context.

Optional live smoke check (not automated; incurs your own API usage): configure your key/model and use a disposable local database with a current tracked-asset price/movement and one persisted source-linked relevant article. Invoke `ContextService(ContextRepository(session), OpenAIProvider()).refresh(demo_user_id)` once from a backend Python session. This checks AI against stored evidence without new market/news calls. Then read `GET /api/dashboard` and verify one qualified card, the actual publisher link, movement, and exact uncertainty disclaimer. Repeat dashboard reads and the service call within the cooldown; they should reuse the stored card. Do not reset/delete the cooldown or retry unavailable output repeatedly. Automated tests fake all AI HTTP responses and use isolated databases; no live OpenAI check was run for this implementation.
