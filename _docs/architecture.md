# MarketLens Architecture

## Decision summary

MarketLens will be built as a **modular monolith**: one React frontend, one FastAPI backend application, and one PostgreSQL database. The backend owns all business logic, database access, external-provider calls, and AI processing.

This is the deliberately simplified MVP architecture. It avoids a task queue, cache service, scheduler, separate worker, authentication system, and microservices while retaining clear module boundaries so those capabilities can be added after the MVP.

```text
React browser application
        |
        | HTTPS + JSON / OpenAPI
        v
FastAPI modular monolith
  |-- HTTP API routes
  |-- application services
  |-- provider adapters
  |-- repositories / ORM
        |
        v
PostgreSQL
        |
        +-- market-data provider
        +-- news provider(s)
        +-- OpenAI API
```

## Selected technology stack

The versions below are the initial baseline, reviewed on 2026-10-19. Dependency versions will be pinned in lockfiles and updated deliberately.

| Area | Choice | Responsibility |
| --- | --- | --- |
| Frontend | React 19.3, TypeScript, Vite 8.1 | Dashboard, watchlist forms, timeline/calendar, refresh controls, and rendering API data. |
| Backend | Python 3.14, FastAPI 0.141.1 | HTTP API, validation, generated OpenAPI contract, business workflows, and provider coordination. |
| Database | PostgreSQL 18.6 | Persistent product data, fetched market/news metadata, refresh state, and historical archive. |
| Data access | SQLAlchemy 2.1 and Alembic 1.20 | ORM mapping and repeatable schema migrations. |
| Charts | Recharts | Price and movement visualizations in the React application. |
| AI | OpenAI API | Structured news classification and short, uncertainty-aware context summaries. |
| External data | One market-data provider and, only if necessary, one news provider | Asset lookup, prices, financial news, and broader contextual news. Provider choice must meet coverage, rate-limit, attribution, and storage requirements. |

The frontend uses the browser's native `fetch` API. No additional client state library is required initially.

## Component responsibilities

### Frontend

The React application is responsible only for user interaction and presentation:

- show the dashboard, watchlist, lots, industries, articles, AI context, and timeline;
- submit user actions to the API;
- show loading, validation, empty, and provider-failure states; and
- retrieve all persisted data through the FastAPI API.

It never connects directly to PostgreSQL or to market, news, or AI providers. API keys and database credentials remain on the backend.

### Backend modules

The FastAPI application remains one deployable service, with internal modules separated by responsibility:

| Module | Responsibility |
| --- | --- |
| API routes | Translate HTTP requests into service calls; validate input; return JSON and appropriate status codes. |
| Asset and ownership service | Manage stocks, ETFs, indices, statuses, purchase lots, weighted-average calculations, and industry suggestions. |
| Dashboard service | Read the stored, user-relevant dashboard projection. |
| Refresh service | Incrementally fetch recent prices and new articles, deduplicate, classify, persist, and record the outcome. |
| Historical-day service | Lazily load a requested day, persist the result, and return stored results on subsequent requests. |
| Relevance and context service | Apply deterministic matching first, then ask the LLM only to resolve ambiguous articles and produce source-linked, non-causal summaries. |
| Provider adapters | Encapsulate each market-data, news, and AI API behind an internal interface. |
| Repositories | Perform database reads and writes; do not contain product workflow decisions. |

Route handlers must not contain provider-specific logic or complex workflows. Services must not know HTTP details. This separation keeps future infrastructure changes local.

### Persistent data

The initial schema will model the relationships needed by the MVP rather than store a single dashboard document. Expected data groups include:

- a seeded `demo_user` and user-owned records;
- assets, exchange/provider identifiers, asset types, and follow status;
- active purchase lots for owned assets;
- industries and asset-to-industry mappings;
- followed industries;
- timestamped price snapshots;
- article metadata only: headline, URL, source, publication time, and supplied snippet;
- article relevance classifications and links to assets and industries;
- AI context summaries with the source articles they reference; and
- refresh and historical-load records with status, timestamps, errors, and provider cursors or watermarks.

Even without login in the MVP, user-created records should have a `user_id` foreign key. A single seeded demo user keeps the user experience simple while avoiding an ownership-data migration when authentication is introduced later.

## Frontend-backend API

The frontend communicates with FastAPI through versioned JSON endpoints under `/api`. FastAPI generates the OpenAPI contract from the route definitions. The contract is the agreement between frontend and backend and documents request shapes, responses, validation errors, and status codes.

Illustrative endpoint groups:

```text
GET    /api/dashboard
GET    /api/assets
GET    /api/assets/search?q=...
POST   /api/assets
PATCH  /api/assets/{asset_id}
DELETE /api/assets/{asset_id}
PUT    /api/assets/{asset_id}/lots
GET    /api/industries
PUT    /api/industries/{industry_id}/follow
POST   /api/refresh
GET    /api/timeline?date=YYYY-MM-DD
```

During development, Vite runs on `localhost:5173` and FastAPI on `localhost:8000`. The frontend is configured with the API base URL. In production, the static frontend may be served by the same deployment or by a static host, but it still calls only the documented API.

## MVP data flows

### Manual refresh

The MVP uses an intentionally simple, synchronous refresh flow:

```text
User selects Refresh
        |
POST /api/refresh
        |
FastAPI refresh service
  -> read last successful refresh / cursor
  -> fetch only newer prices and articles
  -> deduplicate and rule-match articles
  -> classify ambiguous candidates with the LLM
  -> persist snapshots, metadata, links, and summaries
  -> update refresh record
        |
Return result; frontend reloads dashboard data
```

The UI shows an in-progress state for the duration. Refreshes are limited to a small watchlist and bounded article count so they fit normal HTTP request limits. Provider failures return a clear failure state while preserving previously stored dashboard data.

### Lazy historical day

```text
User selects a date in the last 30 days
        |
GET /api/timeline?date=...
        |
Is that day already loaded?
  | yes                         | no
  v                             v
Read stored timeline       Fetch, classify, persist, return
```

The loaded-day record prevents unnecessary repeat provider requests. Historical data already retrieved remains in the personal archive after the initial 30-day request window.

## Environment configuration

All environment-specific values are supplied through environment variables. Secrets are never committed and are not sent to the browser.

| Concern | Development | Test | Production |
| --- | --- | --- | --- |
| Database | Local PostgreSQL, normally Docker | Separate disposable PostgreSQL database | Managed PostgreSQL with backups |
| External providers | Real keys only for controlled manual checks | Fake adapters and fixtures; no network calls | Real keys from deployment secrets |
| AI | Controlled manual checks | Deterministic fake responses | Real API with bounded inputs and error handling |
| Logging | Verbose local logs | Test-runner logs | Structured operational logs |
| Debug | Enabled | Disabled | Disabled |
| CORS | Vite development origin | Usually not applicable | Only deployed frontend origin(s) |
| Demo data | Optional seed data | Test fixtures | Optional public-demo seed only |

Core configuration includes `APP_ENV`, `DATABASE_URL`, `CORS_ORIGINS`, provider API keys, `OPENAI_API_KEY`, `LOG_LEVEL`, and conservative refresh limits. A `DEMO_MODE` flag may seed sample content locally without changing normal product behavior.

## Explicit MVP simplifications

The following are intentional decisions, not omissions:

- one FastAPI process; no separate worker or microservice;
- no Celery, Redis, RabbitMQ, or other job broker;
- no scheduled refreshes, continuous monitoring, alerts, or notifications;
- no dedicated cache service; PostgreSQL and provider watermarks prevent needless work;
- no authentication or multi-user UI; use a seeded demo user;
- no direct provider calls from the frontend;
- no full article-text storage or publisher scraping;
- the minimum practical number of data providers; and
- no real-time streaming or tick-by-tick updates.

PostgreSQL, migrations, stable identifiers, and provider adapters are retained because removing them would make later growth materially harder or create production-only behavior.

## Post-MVP extension path

The architecture is designed so deferred capabilities are additive.

| Post-MVP capability | How it can be added without rewriting the MVP |
| --- | --- |
| Durable background jobs | Have `POST /api/refresh` create a `refresh_run` record, enqueue the existing refresh service through Celery or another queue, and let the frontend poll the run status. |
| Redis/cache service | Add caching within provider adapters; keep PostgreSQL as the durable source of truth. |
| Scheduled refreshes | A scheduler invokes the same refresh service used by manual refresh. |
| Automatic retries | A worker retries failed refresh or historical-load runs using the existing persisted run state and idempotency rules. |
| Authentication and multi-user support | Replace the seeded demo-user selection with authenticated identity; existing `user_id` ownership relations remain valid. |
| Notifications and alerts | Evaluate persisted price snapshots and article events in a new notification service. |
| More provider sources | Implement a new provider adapter and map it to the common normalized price/article models. |
| More asset classes | Extend asset metadata and provider adapters while retaining the common asset and snapshot model. |
| Richer ETF metadata | Add periodic metadata-update jobs and new ETF-related tables without changing the dashboard contract. |
| Real-time updates | Add a streaming or polling delivery layer while preserving the existing stored-data dashboard as the baseline. |

The governing rule is: **routes handle HTTP, services implement workflows, provider adapters call external systems, and repositories persist data.** This keeps the simplified MVP maintainable and provides clear seams for post-MVP growth.
