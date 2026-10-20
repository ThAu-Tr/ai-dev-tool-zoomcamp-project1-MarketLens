from __future__ import annotations

from collections.abc import Iterable


class AssetCatalogueRepository:
    """Read the small, deterministic catalogue supported by the MVP.

    This is deliberately local: live catalogue synchronisation belongs to a
    future provider-backed workflow and must not happen during a picker search.
    """

    _entries = (
        {"name": "ASML Holding", "ticker": "ASML", "exchange": "Euronext Amsterdam", "type": "Stock", "industries": ["Semiconductors"]},
        {"name": "BMW AG", "ticker": "BMW", "exchange": "XETRA", "type": "Stock", "industries": ["Automotive"]},
        {"name": "iShares Global Clean Energy ETF", "ticker": "ICLN", "exchange": "NASDAQ", "type": "ETF", "industries": ["Renewable energy"]},
        {"name": "Vanguard S&P 500 ETF", "ticker": "VOO", "exchange": "NYSE Arca", "type": "ETF", "industries": ["US equities"]},
        {"name": "S&P 500", "ticker": "SPX", "exchange": "S&P Dow Jones Indices", "type": "Index", "industries": ["US equities"]},
    )

    def entries(self) -> Iterable[dict[str, object]]:
        return self._entries
