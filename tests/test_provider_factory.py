from __future__ import annotations

from datetime import date, datetime

from app.provider_factory import ProviderGatewayComposition, create_default_provider_gateway


class FakeMarketProvider:
    def fetch_market_data(self, tickers, since):
        return ("current", tickers, since)

    def fetch_historical_data(self, tickers, market_date):
        return ("historical", tickers, market_date)


class FakeNewsProvider:
    def fetch_news(self, tickers, since):
        return ("news", tickers, since)


def test_composition_routes_each_gateway_call_to_the_matching_provider():
    market = FakeMarketProvider()
    news = FakeNewsProvider()
    gateway = ProviderGatewayComposition(market, news)
    since = datetime(2026, 10, 21)
    day = date(2026, 10, 20)

    assert gateway.fetch_market_data(["SAP"], since) == ("current", ["SAP"], since)
    assert gateway.fetch_historical_data(["SAP"], day) == ("historical", ["SAP"], day)
    assert gateway.fetch_news(["SAP"], since) == ("news", ["SAP"], since)


def test_default_factory_composes_both_adapters_when_both_credentials_exist(monkeypatch):
    monkeypatch.setenv("EODHD_API_KEY", "eodhd-test-key")
    monkeypatch.setenv("MARKETAUX_API_KEY", "marketaux-test-key")
    gateway = create_default_provider_gateway()

    assert isinstance(gateway, ProviderGatewayComposition)
    assert gateway.market_provider._api_key == "eodhd-test-key"
    assert gateway.news_provider.api_key == "marketaux-test-key"


def test_default_factory_is_unavailable_when_no_provider_is_configured(monkeypatch):
    monkeypatch.delenv("EODHD_API_KEY", raising=False)
    monkeypatch.delenv("MARKETAUX_API_KEY", raising=False)
    assert create_default_provider_gateway() is None
