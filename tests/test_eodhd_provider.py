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
        "ASML": "ASML.AS", "BMW": "BMW.XETRA", "AAPL": "AAPL.US",
        "MSFT": "MSFT.US", "NVDA": "NVDA.US", "GOOGL": "GOOGL.US",
        "AMZN": "AMZN.US", "META": "META.US", "TSLA": "TSLA.US",
        "JPM": "JPM.US", "BRK.B": "BRK-B.US", "JNJ": "JNJ.US",
        "LLY": "LLY.US", "V": "V.US", "XOM": "XOM.US", "WMT": "WMT.US",
        "KO": "KO.US", "ORCL": "ORCL.US", "AMD": "AMD.US", "CRM": "CRM.US",
        "ICLN": "ICLN.US", "VOO": "VOO.US", "VTI": "VTI.US", "QQQ": "QQQ.US",
        "VEA": "VEA.US", "IEMG": "IEMG.US", "GLD": "GLD.US",
        "SPX": "GSPC.INDX", "IXIC": "IXIC.INDX", "DJI": "DJI.INDX",
    }
    seen = []
    gateway = EodhdMarketGateway("secret", opener=fake_opener([{
        "close": "812.12345678", "currency": "EUR", "timestamp": 1792584000,
        "previousClose": "802.093", "change_p": "1.2500",
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


def test_weekend_initial_refresh_uses_latest_available_daily_quote_with_bounded_window(monkeypatch):
    class Sunday(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 25)

    monkeypatch.setattr("app.provider_adapters.eodhd.date", Sunday)
    seen = []
    rows = [
        {"date": "2026-10-22", "close": "100.00"},
        {"date": "2026-10-23", "close": "105.50"},
    ]
    gateway = EodhdMarketGateway("secret", opener=fake_opener([{"error": "market closed"}, rows], seen))

    quote = gateway.fetch_market_data(["BMW"], None).quotes[0]

    assert quote.price == Decimal("105.50")
    assert quote.as_of == datetime(2026, 10, 23, tzinfo=UTC)
    assert quote.change_percent == Decimal("5.500")
    assert seen[1][1]["from"] == ["2026-10-11"]
    assert seen[1][1]["to"] == ["2026-10-25"]


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


def test_historical_json_error_payload_is_unavailable_not_market_closed():
    gateway = EodhdMarketGateway("secret", opener=fake_opener([{"error": "rate limit exceeded"}], []))

    result = gateway.fetch_historical_data(["ASML"], date(2026, 10, 20))

    assert result.quotes == []
    assert result.unavailable_tickers == ["ASML"]
    assert result.market_closed is False


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


def test_new_stock_and_index_mappings_use_eodhd_symbols_and_usd_currency():
    seen = []
    gateway = EodhdMarketGateway("secret", opener=fake_opener([
        {"close": "225.50", "currency": "USD", "timestamp": 1792584000, "previousClose": "222.72", "change_p": "1.2482"},
        {"close": "45000", "currency": "USD", "timestamp": 1792584000, "previousClose": "44800", "change_p": "0.4464"},
    ], seen))

    results = gateway.fetch_market_data(["AAPL", "DJI"], None)

    assert [quote.ticker for quote in results.quotes] == ["AAPL", "DJI"]
    assert [quote.currency for quote in results.quotes] == ["USD", "USD"]
    assert results.quotes[0].change_percent == Decimal("1.2482")
    assert results.quotes[1].change_percent is None
    assert "/real-time/AAPL.US" in seen[0][0]
    assert "/real-time/DJI.INDX" in seen[1][0]


def test_index_live_change_is_unavailable_when_previous_close_semantics_are_undocumented():
    seen = []
    gateway = EodhdMarketGateway("secret", opener=fake_opener([{
        "close": "45000", "currency": "USD", "timestamp": 1792584000,
        "previousClose": "44800", "change_p": "0.4464",
    }], seen))

    quote = gateway.fetch_market_data(["SPX"], None).quotes[0]

    assert quote.price == Decimal("45000")
    assert quote.as_of == datetime.fromtimestamp(1792584000, UTC)
    assert quote.change_percent is None
    assert "/real-time/GSPC.INDX" in seen[0][0]


def test_default_gateway_is_configured_from_environment(monkeypatch):
    monkeypatch.setenv("EODHD_API_KEY", "configured")
    monkeypatch.delenv("MARKETAUX_API_KEY", raising=False)
    gateway = create_default_provider_gateway()
    assert isinstance(gateway.market_provider, EodhdMarketGateway)

    monkeypatch.delenv("EODHD_API_KEY")
    assert create_default_provider_gateway() is None
