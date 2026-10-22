# MarketLens

MarketLens is a lightweight investment-monitoring application for everyday investors who want to follow stocks, ETFs, and major indices in one place. It combines price movement with relevant news and carefully qualified AI context so users can understand possible market context without receiving investment advice.

> **Project status:** Phase 2 is in progress. The stored dashboard, supported-asset search, and adding a selected asset to the watchlist are implemented and tested. The remaining MVP features are tracked as GitHub issues.

## The problem

Everyday investors often need to piece together price movements, company news, industry developments, and wider events from separate sources. That makes it difficult to understand what may be relevant today or to revisit the context around a past market day.

MarketLens brings those inputs into a combined dashboard and, later in the MVP, a persistent historical timeline. It is a monitoring and context tool—not a trading system, portfolio optimiser, or source of investment recommendations.

## What exists today

The following vertical slices are complete:

- A persisted, read-only dashboard through `GET /api/dashboard`, including empty, error, and uncertainty-aware AI-context states.
- A deterministic catalogue search for supported Stocks, ETFs, and Indices through `GET /api/assets/search`.
- Catalogue-validated creation of an Owned or Interested watchlist asset through `POST /api/assets`.
- PostgreSQL-oriented persistence with Alembic migrations and a seeded demo-user model.
- Backend tests, React component/API tests, and a production frontend build check.

See the completed work in [issue #1](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/1), [issue #2](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/2), and [issue #3](https://github.com/ThAu-Tr/ai-dev-tool-zoomcamp-project1-MarketLens/issues/3).

## Demo

There is no deployed demo, video, or screenshot yet.

// TODO: Add a short demo recording or screenshots once the main MVP flow is complete and runnable end to end.

## MVP scope

The planned MVP lets a single demo user:

1. Follow Stocks, ETFs, and major Indices as Owned or Interested.
2. Record active purchase lots for Owned Stocks and ETFs.
3. Follow industries and review suggested industries based on tracked assets.
4. Refresh stored prices and categorized news context.
5. Read uncertainty-aware, source-linked AI context summaries.
6. Load historical price movements for individual days within the initial 30-day request window and reuse stored results.

The product deliberately excludes trading, broker integrations, authentication, real-time alerts, full portfolio accounting, crypto, and investment recommendations. Read the complete [product specification](_docs/plan.md).
Historical news, AI-generated historical context, and the complete archived-day experience are planned as post-MVP extensions (#15 and #16).

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
uv run pytest
```

Frontend tests and production build:

```powershell
npm --prefix frontend run test
npm --prefix frontend run build
```

The current backend suite covers the completed dashboard, catalogue-search, and asset-creation slices. The frontend suite covers their API clients and UI states.

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

The frontend uses `VITE_API_BASE_URL` when it needs a non-default API origin. Provider credentials are not used by the currently completed features and must never be exposed to the browser.

// TODO: Add a verified, reproducible full-stack local-development guide, including PostgreSQL provisioning, the FastAPI start command, frontend API-origin configuration, and CORS setup.

## Testing and quality

The project adds tests with each completed vertical feature. Tests use deterministic local data and must not call live market, news, or AI services.

// TODO: Add end-to-end integration-test instructions once the main MVP workflows are complete.

## Important design decisions

- **Simple deployment shape:** one React frontend, one FastAPI application, and PostgreSQL; no queue, cache service, scheduler, microservices, or authentication for the MVP.
- **Contract-first boundary:** [openapi.yaml](openapi.yaml) describes the API expected by the frontend.
- **Single demo user:** data carries an ownership relationship so authentication can be added later without restructuring the core model.
- **Exact financial values:** money and quantities are represented as exact decimals rather than binary floating-point values.
- **Safety:** AI-produced context must be uncertainty-aware, link to supporting sources, and never give investment advice or make definitive causal claims.

## Limitations and future work

The current implementation is intentionally incomplete: it has no live market or news provider integration, refresh workflow, industry management, purchase-lot editor, history UI, authentication, deployment, CI, or operational monitoring.

// TODO: Replace this section with deployed-system limitations and prioritized post-MVP work once the MVP feature backlog is complete.

## Deployment and CI/CD

No public deployment or continuous-integration workflow exists yet.

// TODO: Document containerization, hosted services, required deployment secrets, CI checks, and the public demo URL after the productionization phase.


### AI context (issue #13)

Set optional `OPENAI_API_KEY` in the ignored backend `.env`; `OPENAI_MODEL` defaults to `gpt-6-luna` with low reasoning effort. Apply the additive Alembic migration before running the feature. No new Python or frontend packages are required.

Only manual refresh triggers AI, after prices and news have been committed. AI reads stored metadata and current movements (recent 72-hour evidence); it never requests extra market/news data. Each user has a persistent one-hour cooldown, at most two AI calls per eligible refresh, at most five ambiguous articles, five tracked assets, twelve classified articles (three per asset), 500 snippet characters per article, 1,200 output tokens per call, a 12-second timeout, and no automatic retries. Missing credentials, invalid output and quota failures leave successful market/news refresh intact. Unclassified/Not Relevant candidates remain hidden from the feed. Summaries are reused across restarts when evidence is unchanged and replaced per asset only after valid changed output.

The LLM selects classifications with verified source quotations and persisted article IDs. It selects up to two relevant reports per summary; the service renders a short qualified card using their exact headlines and the stored movement. This constrained rendering keeps model-authored advice, causal claims, fabricated sources and unsupported confidence scores out of cards. Unsafe/instructional headlines are omitted. The persistent UI disclaimer still applies; source relevance is uncertain and the bounded evidence window may omit useful context.

Optional live smoke check (not automated; incurs your own API usage): configure your key/model and use a disposable local database with a current tracked-asset price/movement and one persisted source-linked relevant article. Invoke `ContextService(ContextRepository(session), OpenAIProvider()).refresh(demo_user_id)` once from a backend Python session. This checks AI against stored evidence without new market/news calls. Then read `GET /api/dashboard` and verify one qualified card, the actual publisher link, movement, and exact uncertainty disclaimer. Repeat dashboard reads and the service call within the cooldown; they should reuse the stored card. Do not reset/delete the cooldown or retry unavailable output repeatedly. Automated tests fake all AI HTTP responses and use isolated databases; no live OpenAI check was run for this implementation.
