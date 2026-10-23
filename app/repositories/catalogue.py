from __future__ import annotations

from collections.abc import Iterable


class AssetCatalogueRepository:
    """Read the versioned local MVP catalogue; picker searches never call providers."""

    # Intentionally bounded and curated rather than a promise of full-market
    # coverage. Keep provider symbols in eodhd.EODHD_SYMBOLS where available.
    _entries = (
        {"name": "ASML Holding", "ticker": "ASML", "exchange": "Euronext Amsterdam", "type": "Stock", "industries": ["Semiconductors"]},
        {"name": "BMW AG", "ticker": "BMW", "exchange": "XETRA", "type": "Stock", "industries": ["Automotive"]},
        {"name": "Apple Inc.", "ticker": "AAPL", "exchange": "NASDAQ", "type": "Stock", "industries": ["Technology hardware"]},
        {"name": "Microsoft Corporation", "ticker": "MSFT", "exchange": "NASDAQ", "type": "Stock", "industries": ["Enterprise software"]},
        {"name": "NVIDIA Corporation", "ticker": "NVDA", "exchange": "NASDAQ", "type": "Stock", "industries": ["Semiconductors"]},
        {"name": "Alphabet Inc.", "ticker": "GOOGL", "exchange": "NASDAQ", "type": "Stock", "industries": ["Communication services"]},
        {"name": "Amazon.com, Inc.", "ticker": "AMZN", "exchange": "NASDAQ", "type": "Stock", "industries": ["Consumer discretionary"]},
        {"name": "Meta Platforms, Inc.", "ticker": "META", "exchange": "NASDAQ", "type": "Stock", "industries": ["Communication services"]},
        {"name": "Tesla, Inc.", "ticker": "TSLA", "exchange": "NASDAQ", "type": "Stock", "industries": ["Automotive"]},
        {"name": "JPMorgan Chase & Co.", "ticker": "JPM", "exchange": "NYSE", "type": "Stock", "industries": ["Banking"]},
        {"name": "Berkshire Hathaway Inc.", "ticker": "BRK.B", "exchange": "NYSE", "type": "Stock", "industries": ["Financial services"]},
        {"name": "Johnson & Johnson", "ticker": "JNJ", "exchange": "NYSE", "type": "Stock", "industries": ["Healthcare"]},
        {"name": "Eli Lilly and Company", "ticker": "LLY", "exchange": "NYSE", "type": "Stock", "industries": ["Healthcare"]},
        {"name": "Visa Inc.", "ticker": "V", "exchange": "NYSE", "type": "Stock", "industries": ["Financial services"]},
        {"name": "Exxon Mobil Corporation", "ticker": "XOM", "exchange": "NYSE", "type": "Stock", "industries": ["Energy"]},
        {"name": "Walmart Inc.", "ticker": "WMT", "exchange": "NYSE", "type": "Stock", "industries": ["Consumer staples"]},
        {"name": "The Coca-Cola Company", "ticker": "KO", "exchange": "NYSE", "type": "Stock", "industries": ["Consumer staples"]},
        {"name": "Oracle Corporation", "ticker": "ORCL", "exchange": "NYSE", "type": "Stock", "industries": ["Enterprise software"]},
        {"name": "Advanced Micro Devices, Inc.", "ticker": "AMD", "exchange": "NASDAQ", "type": "Stock", "industries": ["Semiconductors"]},
        {"name": "Salesforce, Inc.", "ticker": "CRM", "exchange": "NYSE", "type": "Stock", "industries": ["Enterprise software"]},
        {"name": "iShares Global Clean Energy ETF", "ticker": "ICLN", "exchange": "NASDAQ", "type": "ETF", "industries": ["Renewable energy"]},
        {"name": "Vanguard S&P 500 ETF", "ticker": "VOO", "exchange": "NYSE Arca", "type": "ETF", "industries": ["US equities"]},
        {"name": "Vanguard Total Stock Market ETF", "ticker": "VTI", "exchange": "NYSE Arca", "type": "ETF", "industries": ["US equities"]},
        {"name": "Invesco QQQ Trust", "ticker": "QQQ", "exchange": "NASDAQ", "type": "ETF", "industries": ["Technology"]},
        {"name": "Vanguard FTSE Developed Markets ETF", "ticker": "VEA", "exchange": "NYSE Arca", "type": "ETF", "industries": ["International equities"]},
        {"name": "iShares Core MSCI Emerging Markets ETF", "ticker": "IEMG", "exchange": "NYSE Arca", "type": "ETF", "industries": ["Emerging markets"]},
        {"name": "SPDR Gold Shares", "ticker": "GLD", "exchange": "NYSE Arca", "type": "ETF", "industries": ["Commodities"]},
        {"name": "S&P 500", "ticker": "SPX", "exchange": "S&P Dow Jones Indices", "type": "Index", "industries": ["US equities"]},
        {"name": "NASDAQ Composite", "ticker": "IXIC", "exchange": "NASDAQ", "type": "Index", "industries": ["Technology"]},
        {"name": "Dow Jones Industrial Average", "ticker": "DJI", "exchange": "S&P Dow Jones Indices", "type": "Index", "industries": ["US equities"]},
    )

    def entries(self) -> Iterable[dict[str, object]]:
        return self._entries
