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

The owner reports verifying CI/CD deployment, saved watchlist data after a restart, and a Render dashboard rollback; these were not independently repeated for this documentation update. To smoke-check, open the live URL, add a watchlist asset, and verify it persists after a service restart.

To roll back, open the service's **Deploys** page in the [Render Dashboard](https://dashboard.render.com/), choose a previous successful deploy, and select **Rollback**. A dashboard rollback disables automatic deploys; re-enable them from the service **Settings** page when ready. A code rollback does not roll back Neon schema migrations or database data, so confirm the selected application version is compatible with the current database schema. See [Render's rollback guide](https://render.com/docs/rollbacks).

For local persistence verification, save an asset and any purchase lots, restart using the [README Compose instructions](../../README.md#run-with-docker-compose), and confirm the data remains. Inspect startup/migration logs with `docker compose --env-file .env --env-file .env.compose logs app`.
