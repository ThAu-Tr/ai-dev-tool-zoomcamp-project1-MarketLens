from __future__ import annotations

import os
from pathlib import Path


def load_local_env() -> None:
    """Load a local ignored .env without overriding deployment environment."""
    env_file = Path.cwd() / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("\"'")
        if key and key.replace("_", "").isalnum():
            os.environ.setdefault(key, value)


load_local_env()


def database_url() -> str:
    """Return the configured database URL without embedding environment secrets."""
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL must be set before starting the MarketLens backend.")
    return value


def cors_allowed_origins() -> list[str]:
    """Return the exact origins allowed to call the API from a browser."""
    configured_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    if "*" in origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must list exact origins; '*' is not allowed.")
    return origins
