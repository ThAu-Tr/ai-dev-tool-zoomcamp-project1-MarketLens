"""Default provider composition for application startup.

Keep provider construction here so adding another adapter does not change the
injection seam used by tests or mix provider setup into route handlers.
"""
from __future__ import annotations

import os

from app.provider_adapters.eodhd import EodhdMarketGateway


def create_default_provider_gateway():
    if not os.getenv("EODHD_API_KEY"):
        return None
    return EodhdMarketGateway()
