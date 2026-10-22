"""Default provider composition for application startup.

Keep provider construction here so adding another adapter does not change the
injection seam used by tests or mix provider setup into route handlers.
"""
from __future__ import annotations

import os

from app.adapters.marketaux import MarketauxProvider
from app.provider_adapters.eodhd import EodhdMarketGateway


class ProviderGatewayComposition:
    """Combine market and news providers behind the existing gateway seam."""

    def __init__(self, market_provider: EodhdMarketGateway, news_provider: MarketauxProvider) -> None:
        self.market_provider = market_provider
        self.news_provider = news_provider

    def fetch_market_data(self, tickers, since):
        return self.market_provider.fetch_market_data(tickers, since)

    def fetch_historical_data(self, tickers, market_date):
        return self.market_provider.fetch_historical_data(tickers, market_date)

    def fetch_news(self, tickers, since, industries=None):
        return self.news_provider.fetch_news(tickers, since, industries)

    def fetch_market_context(self, since, tickers=None):
        return self.news_provider.fetch_market_context(since, tickers)

    def generate_context(self) -> None:
        return None


def create_default_provider_gateway():
    if not os.getenv("EODHD_API_KEY") and not os.getenv("MARKETAUX_API_KEY"):
        return None
    return ProviderGatewayComposition(EodhdMarketGateway(), MarketauxProvider())
