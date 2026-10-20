from __future__ import annotations

import os


def database_url() -> str:
    """Return the configured database URL without embedding environment secrets."""
    value = os.getenv("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL must be set before starting the MarketLens backend.")
    return value
