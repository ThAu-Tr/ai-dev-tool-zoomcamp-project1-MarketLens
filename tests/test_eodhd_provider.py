from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit

from app.providers import MarketDataResult
from app.provider_adapters.eodhd import EodhdError, EodhdMarketGateway, EODHD_SYMBOLS
from app.provider_factory import create_default_provider_gateway


class Response:
    def __init__(self, payload):
        import json
        self.body = json.dumps(payload).encode()

    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.body


def fake_opener(responses, seen):
    def open(url, timeout):
        parsed = urlsplit(url)
        seen.append((parsed.path, parse_qs(parsed.query), timeout))
        payload = responses.pop(0)
        if isinstance(payload, Exception):
            raise payload
        return Response(payload)
    return open


def test_symbol_mapping_and_realtime_normalization_return_catalogue_ticker():
    assert EODHD_SYMBOLS == {
        "ASML": "ASML.AS", "BMW": "BMW.XETRA", "ICLN": "ICLN.US",
        "VOO": "VOO.US", "SPX": "GSPC.INDX",
    }
    seen = []
    gateway = EodhdMarketGateway("secret", opener=fake_opener([{
        "close": "812.12345678", "currency": "EUR", "timestamp": 1792584000,
        "change_p": "1.2500",
    }], seen))
    result = gateway.fetch_market_data(["ASML"], None)
    assert isinstance(result, MarketDataResult)
    quote = result.quotes[0]
    assert (quote.ticker, quote.price, quote.currency, quote.change_percent) == (
        "ASML", Decimal("812.12345678"), "EUR", Decimal("1.2500"),
    )
    assert quote.as_of == datetime.fromtimestamp(1792584000, UTC)
    assert "/real-time/ASML.AS" in seen[0][0]
    assert seen[0][1]["api_token"] == ["secret"]


def test_realtime_rejection_falls_back_to_daily_close_and_uses_observed_movement():
    seen = []
    rows = [
        {"date": "2026-10-20", "close": "100.00", "adjusted_close": "100.00"},
        {"date": "2026-10-21", "close": "105.50", "adjusted_close": "105.50"},
    ]
    gateway = EodhdMarketGateway("secret", opener=fake_opener([{"error": "unsupported"}, rows], seen))
    quote = gateway.fetch_market_data(["BMW"], None).quotes[0]
    assert quote.ticker == "BMW"
    assert quote.price == Decimal("105.50")
    assert quote.currency == "EUR"
    assert quote.change_percent == Decimal("5.500")
    assert quote.as_of == datetime(2026, 10, 21, tzinfo=UTC)
    assert "/eod/BMW.XETRA" in seen[1][0]


def test_historical_exact_date_path_does_not_use_latest_row():
    seen = []
    gateway = EodhdMarketGateway("secret", opener=fake_opener([[
        {"date": "2026-10-20", "close": "11.25"},
        {"date": "2026-10-21", "close": "999"},
    ]], seen))
    result = gateway.fetch_historical_data(["SPX"], date(2026, 10, 20))
    quote = result.quotes[0]
    assert quote.ticker == "SPX" and quote.price == Decimal("11.25")
    assert quote.currency == "USD" and quote.change_percent is None
    assert quote.as_of == datetime(2026, 10, 20, tzinfo=UTC)
    assert "/eod/GSPC.INDX" in seen[0][0]
    assert seen[0][1]["from"] == seen[0][1]["to"] == ["2026-10-20"]


def test_missing_historical_rows_identify_partial_coverage_or_closed_day():
    seen = []
    gateway = EodhdMarketGateway("secret", opener=fake_opener([[
        {"date": "2026-10-20", "close": "22"},
    ], []], seen))
    partial = gateway.fetch_historical_data(["ASML", "VOO"], date(2026, 10, 20))
    assert [quote.ticker for quote in partial.quotes] == ["ASML"]
    assert partial.unavailable_tickers == ["VOO"]

    closed_gateway = EodhdMarketGateway("secret", opener=fake_opener([[], []], []))
    closed = closed_gateway.fetch_historical_data(["ASML", "VOO"], date(2026, 10, 18))
    assert closed.market_closed is True and closed.unavailable_tickers == []


def test_unsupported_symbols_and_provider_errors_are_explicit_and_redacted():
    seen = []
    gateway = EodhdMarketGateway("secret-key", opener=fake_opener([TimeoutError("secret-key leaked"), TimeoutError("secret-key leaked")], seen))
    result = gateway.fetch_market_data(["UNKNOWN", "VOO"], None)
    assert result.unavailable_tickers == ["UNKNOWN", "VOO"]
    failing = EodhdMarketGateway("secret-key", opener=lambda url, timeout: (_ for _ in ()).throw(TimeoutError("secret-key leaked")))
    try:
        failing._get("eod/VOO.US")
    except EodhdError as error:
        assert "secret-key" not in str(error)
        assert error.__cause__ is None


def test_missing_key_is_reported_as_unavailable_without_http():
    gateway = EodhdMarketGateway("")
    result = gateway.fetch_market_data(["ASML"], None)
    assert result.quotes == [] and result.unavailable_tickers == ["ASML"]


def test_default_gateway_is_configured_from_environment(monkeypatch):
    monkeypatch.setenv("EODHD_API_KEY", "configured")
    gateway = create_default_provider_gateway()
    assert isinstance(gateway, EodhdMarketGateway)

    monkeypatch.delenv("EODHD_API_KEY")
    assert create_default_provider_gateway() is None
