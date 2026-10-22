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
