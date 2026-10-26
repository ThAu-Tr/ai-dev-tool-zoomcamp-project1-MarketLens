# Render deployment and rollback

Detailed deployment notes for MarketLens. For the quickest local installation, see the [README Docker quick start](../../README.md#quick-start-with-docker-compose).

## Render deployment

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

For local Compose persistence checks, add an asset to the watchlist and, if marking it Owned, save purchase lots. Stop and restart using the [README Compose instructions](../../README.md#run-with-docker-compose), then confirm the asset and lots remain. `docker compose --env-file .env --env-file .env.compose logs app` shows startup and migration output. This local setup does not publish the app to the internet.
