from __future__ import annotations

from datetime import date, datetime
import os
from pathlib import Path
import subprocess
import sys

from app.provider_factory import ProviderGatewayComposition, create_default_provider_gateway


class FakeMarketProvider:
    def fetch_market_data(self, tickers, since):
        return ("current", tickers, since)

    def fetch_historical_data(self, tickers, market_date):
        return ("historical", tickers, market_date)


class FakeNewsProvider:
    def fetch_news(self, tickers, since, industries=None):
        return ("news", tickers, since, industries)


def test_composition_routes_each_gateway_call_to_the_matching_provider():
    market = FakeMarketProvider()
    news = FakeNewsProvider()
    gateway = ProviderGatewayComposition(market, news)
    since = datetime(2026, 10, 21)
    day = date(2026, 10, 20)

    assert gateway.fetch_market_data(["SAP"], since) == ("current", ["SAP"], since)
    assert gateway.fetch_historical_data(["SAP"], day) == ("historical", ["SAP"], day)
    assert gateway.fetch_news(["SAP"], since, ["Software"]) == ("news", ["SAP"], since, ["Software"])


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


def test_fastapi_startup_loads_provider_keys_from_local_env(tmp_path: Path):
    project_root = Path(__file__).resolve().parents[1]
    (tmp_path / ".env").write_text(
        "EODHD_API_KEY=test-eodhd-key\nMARKETAUX_API_KEY=test-marketaux-key\n",
        encoding="utf-8",
    )
    child_env = os.environ.copy()
    child_env.pop("EODHD_API_KEY", None)
    child_env.pop("MARKETAUX_API_KEY", None)
    child_env["PYTHONPATH"] = str(project_root)
    code = (
        "import app.main; "
        "from app.provider_factory import create_default_provider_gateway; "
        "gateway = create_default_provider_gateway(); "
        "assert gateway is not None; "
        "assert gateway.news_provider.api_key == 'test-marketaux-key'; "
        "assert gateway.market_provider._api_key == 'test-eodhd-key'; "
        "print('local env loaded')"
    )

    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=child_env,
        capture_output=True, text=True, timeout=15, check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "local env loaded"
