# Testing and verification

This document covers automated checks and optional live provider smoke tests. Live checks use your own EODHD or Marketaux account and API quota; automated tests use fakes/mocks.

## Automated checks and test coverage

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

`tests/integration/` is the separately runnable HTTP-to-database workflow suite. It covers adding and managing an asset before reading the dashboard, refreshing and persisting prices/news/AI context before reading the dashboard, and loading then revisiting a historical day. The full backend suite also includes it.

Additional tests cover watchlist changes, purchase lots, catalogue search, news, AI context, timeline and error handling. API/persistence tests use isolated SQLite where applicable; provider adapter and composition tests use fakes and do not prove live provider connectivity.

The integration suite uses an isolated in-memory SQLite database and deterministic fake providers, so it makes no live market, news, or AI calls. SQLite test results do not establish PostgreSQL compatibility or real provider integration. PostgreSQL and live-provider behavior require separate verification; optional provider smoke checks follow.

## Marketaux smoke check

To manually smoke-check Marketaux after provider composition is enabled, configure `MARKETAUX_API_KEY` in the backend environment and run one dashboard refresh with one or more tracked symbols. Confirm the refresh completes, then inspect `GET /api/dashboard` for metadata-only articles and source links. The adapter makes separate bounded queries for tracked symbols and followed industries (at most two requests, with three results per request); use your own account and quota.

## EODHD smoke check (manual, uses your account)

After migrations, start the backend with `EODHD_API_KEY` set and request `POST /api/refresh` once. Confirm the response succeeds and `GET /api/dashboard` shows an `asOf` timestamp and currency supplied by the provider. Then request `GET /api/timeline?date=YYYY-MM-DD` for one eligible date with known EODHD coverage and confirm its `source` is `newly-loaded`; request the same date again and confirm `source` is `archive`. The second request should not call EODHD. Each refresh may try the intraday endpoint and then fall back to daily closes; use one tracked asset and avoid repeated retries to stay within the free account's daily request limit.
