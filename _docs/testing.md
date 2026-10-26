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

`tests/integration/` is the separately runnable HTTP-to-database workflow suite. It covers adding and managing an asset before reading the dashboard, refreshing and persisting prices/news/AI context before reading the dashboard, and loading then revisiting a historical day. Run it with `uv run pytest tests/integration`; the full backend suite also includes it.

The existing `tests/test_asset_creation.py`, `test_asset_ownership.py`, `test_purchase_lots.py`, `test_refresh.py`, `test_direct_news.py`, `test_ai_context.py`, and `test_timeline.py` contain additional API/service persistence and failure cases. Industry, dashboard, and asset-removal tests likewise exercise HTTP routes against isolated SQLite. `test_asset_catalogue.py` exercises catalogue search through HTTP and tests its service directly; it does not access a database. `test_eodhd_provider.py`, `test_marketaux.py`, and `test_provider_factory.py` focus on provider adapters and composition; they use fakes and do not establish live provider connectivity. Some service and repository logic is tested directly in `test_ai_context.py` and provider-specific tests.

The integration suite uses an isolated in-memory SQLite database and deterministic fake providers, so it makes no live market, news, or AI calls. SQLite test results do not establish PostgreSQL compatibility or real provider integration. Those require the separate manual PostgreSQL/provider smoke checks described below.

## Marketaux smoke check

To manually smoke-check Marketaux after provider composition is enabled, configure `MARKETAUX_API_KEY` in the backend environment and run one dashboard refresh with one or more tracked symbols. Confirm the refresh completes, then inspect `GET /api/dashboard` for metadata-only articles and source links. The adapter makes separate bounded queries for tracked symbols and followed industries (at most two requests, with three results per request); this live check is optional and must use your own account and quota. Automated tests mock HTTP and do not call Marketaux.

## EODHD smoke check (manual, uses your account)

After migrations, start the backend with `EODHD_API_KEY` set and request `POST /api/refresh` once. Confirm the response succeeds and `GET /api/dashboard` shows an `asOf` timestamp and currency supplied by the provider. Then request `GET /api/timeline?date=YYYY-MM-DD` for one eligible date with known EODHD coverage and confirm its `source` is `newly-loaded`; request the same date again and confirm `source` is `archive`. The second request should not call EODHD. Each refresh may try the intraday endpoint and then fall back to daily closes; use one tracked asset and avoid repeated retries to stay within the free account's daily request limit. Adapter tests mock HTTP and never consume API calls.
