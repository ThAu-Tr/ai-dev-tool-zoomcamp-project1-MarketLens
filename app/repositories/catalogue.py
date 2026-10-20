from __future__ import annotations

from collections.abc import Iterable


class AssetCatalogueRepository:
    """Read the small, deterministic catalogue supported by the MVP.

    This is deliberately local: live catalogue synchronisation belongs to a
    future provider-backed workflow and must not happen during a picker search.
    """

    _entries = (
        {"name": "ASML Holding", "ticker": "ASML", "exchange": "Euronext Amsterdam", "type": "Stock"},
        {"name": "BMW AG", "ticker": "BMW", "exchange": "XETRA", "type": "Stock"},
        {"name": "iShares Global Clean Energy ETF", "ticker": "ICLN", "exchange": "NASDAQ", "type": "ETF"},
        {"name": "Vanguard S&P 500 ETF", "ticker": "VOO", "exchange": "NYSE Arca", "type": "ETF"},
        {"name": "S&P 500", "ticker": "SPX", "exchange": "S&P Dow Jones Indices", "type": "Index"},
    )

    def entries(self) -> Iterable[dict[str, str]]:
        return self._entries
