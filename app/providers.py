from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class MarketQuote:
    """Normalized quote returned by a market-data adapter."""

    ticker: str
    price: Decimal
    currency: str
    change_percent: Decimal | None
    as_of: datetime


@dataclass(frozen=True)
class MarketDataResult:
    quotes: list[MarketQuote]
    unavailable_tickers: list[str] = None  # type: ignore[assignment]
    market_closed: bool = False

    def __post_init__(self) -> None:
        if self.unavailable_tickers is None:
            object.__setattr__(self, "unavailable_tickers", [])


class ProviderGateway(Protocol):
    """Boundary for external market, news, and AI adapters.

    Dashboard reads deliberately receive this boundary but must never use it.
    Refresh and historical workflows will call concrete adapters in later issues.
    """

    def fetch_market_data(self, tickers: list[str], since: datetime | None) -> MarketDataResult | list[MarketQuote]: ...

    def fetch_news(self) -> None: ...

    def generate_context(self) -> None: ...
