Documents

- `_docs/process.md` - how work is organized

Keep changes within the MVP. Prefer small, understandable vertical changes and do not change unrelated files.

Commands

- `uv sync` — install or synchronize Python dependencies.
- `uv run pytest` — run the backend and integration test suite.
- `uv run pytest tests/path/to/test_file.py` — run one backend test file.
- `npm --prefix frontend run dev` — run the React/Vite frontend after it is scaffolded.

Non-negotiable rules

- Preserve the architecture: React frontend → FastAPI HTTP/JSON API → PostgreSQL. The frontend never accesses the database or external providers directly.
- Do not add, remove, or upgrade dependencies without asking. Declare approved dependencies only in `pyproject.toml` or `frontend/package.json`.
- Do not hardcode secrets or environment-specific configuration.
- Use Alembic migrations for schema changes. Store money and quantities as exact decimals, never binary floats.
- Keep external-provider calls in provider adapters and business workflows in services, not route handlers or React components.
- Add or update tests for important behavior. Tests must not call live market, news, or AI services.
- Keep AI output uncertainty-aware: no investment advice or definitive causal claims.
