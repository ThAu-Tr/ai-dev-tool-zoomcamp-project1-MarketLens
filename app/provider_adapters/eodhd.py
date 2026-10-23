from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
import os
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.providers import MarketDataResult, MarketQuote


# EODHD symbols are exchange-specific; API values are always translated back
# to the catalogue ticker before crossing the provider boundary.
EODHD_SYMBOLS = {
    "ASML": "ASML.AS",
    "BMW": "BMW.XETRA",
    "AAPL": "AAPL.US",
    "MSFT": "MSFT.US",
    "NVDA": "NVDA.US",
    "GOOGL": "GOOGL.US",
    "AMZN": "AMZN.US",
    "META": "META.US",
    "TSLA": "TSLA.US",
    "JPM": "JPM.US",
    "BRK.B": "BRK-B.US",
    "JNJ": "JNJ.US",
    "LLY": "LLY.US",
    "V": "V.US",
    "XOM": "XOM.US",
    "WMT": "WMT.US",
    "KO": "KO.US",
    "ORCL": "ORCL.US",
    "AMD": "AMD.US",
    "CRM": "CRM.US",
    "ICLN": "ICLN.US",
    "VOO": "VOO.US",
    "VTI": "VTI.US",
    "QQQ": "QQQ.US",
    "VEA": "VEA.US",
    "IEMG": "IEMG.US",
    "GLD": "GLD.US",
    "SPX": "GSPC.INDX",
    "IXIC": "IXIC.INDX",
    "DJI": "DJI.INDX",
}
EODHD_CURRENCIES = {"ASML": "EUR", "BMW": "EUR", **{ticker: "USD" for ticker in EODHD_SYMBOLS if ticker not in {"ASML", "BMW"}}}
EODHD_INDEX_TICKERS = {"SPX", "IXIC", "DJI"}
EODHD_API = "https://eodhd.com/api"


class EodhdError(RuntimeError):
    """A safe provider failure; response bodies and credentials are excluded."""


class EodhdMarketGateway:
    def __init__(self, api_key: str | None = None, *, opener: Callable = urlopen, timeout: float = 10) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("EODHD_API_KEY")
        self._opener = opener
        self._timeout = timeout

    def fetch_market_data(self, tickers: list[str], since: datetime | None) -> MarketDataResult:
        if not self._api_key:
            return MarketDataResult([], list(tickers))
        quotes: list[MarketQuote] = []
        unavailable: list[str] = []
        for ticker in tickers:
            symbol = EODHD_SYMBOLS.get(ticker.upper())
            if symbol is None:
                unavailable.append(ticker)
                continue
            try:
                # Real-time quotes are attempted first. The account may not have
                # intraday access, so a failed or unsupported quote falls back
                # to the most recent daily close.
                try:
                    data = self._get(f"real-time/{symbol}")
                    quote = self._quote_from_realtime(ticker, data)
                except EodhdError:
                    quote = None
                if quote is None:
                    end = date.today()
                    rows = self._get(f"eod/{symbol}", {"from": (end - timedelta(days=14)).isoformat(), "to": end.isoformat(), "period": "d"})
                    quote = self._quote_from_daily(ticker, rows, with_movement=True)
                if quote is None:
                    unavailable.append(ticker)
                else:
                    quotes.append(quote)
            except EodhdError:
                unavailable.append(ticker)
        return MarketDataResult(quotes, unavailable)

    def fetch_historical_data(self, tickers: list[str], market_date: date) -> MarketDataResult:
        if not self._api_key:
            return MarketDataResult([], list(tickers))
        quotes: list[MarketQuote] = []
        unavailable: list[str] = []
        for ticker in tickers:
            symbol = EODHD_SYMBOLS.get(ticker.upper())
            if symbol is None:
                unavailable.append(ticker)
                continue
            try:
                rows = self._get(f"eod/{symbol}", {"from": market_date.isoformat(), "to": market_date.isoformat(), "period": "d"})
                if not isinstance(rows, list) or any(
                    isinstance(row, dict) and ("error" in row or "errors" in row)
                    for row in rows
                ):
                    # EODHD may return an HTTP-success JSON error payload. Only
                    # an empty array represents a confirmed no-observation day.
                    raise EodhdError("The market-data provider returned an invalid historical response.")
                row = self._row_for_date(rows, market_date)
                if row is None:
                    continue
                quote = self._quote_from_row(ticker, row, None)
                if quote:
                    quotes.append(quote)
                else:
                    unavailable.append(ticker)
            except EodhdError:
                unavailable.append(ticker)
        # A date with no rows for every supported symbol is a holiday/weekend.
        if quotes:
            observed = {quote.ticker.upper() for quote in quotes}
            unavailable.extend(ticker for ticker in tickers if ticker.upper() not in observed and ticker not in unavailable)
        return MarketDataResult(quotes, unavailable, market_closed=not quotes and not unavailable)

    def _get(self, endpoint: str, params: dict[str, str] | None = None):
        query = {"api_token": self._api_key, "fmt": "json", **(params or {})}
        request_url = f"{EODHD_API}/{endpoint}?{urlencode(query)}"
        try:
            with self._opener(request_url, timeout=self._timeout) as response:
                body = response.read()
            return json.loads(body)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError):
            # Never include URL or upstream text in errors; the URL contains the key.
            raise EodhdError("The market-data provider request failed.") from None

    @staticmethod
    def _quote_from_realtime(ticker: str, data: object) -> MarketQuote | None:
        if not isinstance(data, dict):
            return None
        try:
            price = _decimal(data.get("close", data.get("price")))
            currency = _currency(data.get("currency") or EODHD_CURRENCIES[ticker.upper()])
            raw_timestamp = data.get("timestamp")
            if raw_timestamp is not None:
                as_of = datetime.fromtimestamp(int(raw_timestamp), UTC)
            elif data.get("date"):
                as_of = _parse_datetime(data["date"])
            else:
                return None
            # EODHD documents the live change_p/previousClose fields for its
            # live stock and ETF quote contract, but does not establish that
            # same comparison baseline for indices. Keep an index price while
            # withholding an unverified movement from this endpoint.
            movement = None if ticker.upper() in EODHD_INDEX_TICKERS else data.get("change_p")
            change_percent = _decimal(movement) if movement is not None else None
            if price < 0:
                return None
            return MarketQuote(ticker, price, currency, change_percent, as_of)
        except (ValueError, TypeError, InvalidOperation, KeyError, OverflowError):
            return None

    @classmethod
    def _quote_from_daily(cls, ticker: str, rows: object, *, with_movement: bool) -> MarketQuote | None:
        if not isinstance(rows, list):
            return None
        valid = [row for row in rows if isinstance(row, dict) and _valid_row(row)]
        valid.sort(key=lambda row: row["date"])
        if not valid:
            return None
        row = valid[-1]
        previous = valid[-2] if with_movement and len(valid) > 1 else None
        movement = None
        if previous:
            prev_close = _decimal(previous.get("close", previous.get("adjusted_close")))
            close = _decimal(row.get("close", row.get("adjusted_close")))
            if prev_close:
                movement = (close - prev_close) / prev_close * Decimal("100")
        return cls._quote_from_row(ticker, row, movement)

    @staticmethod
    def _row_for_date(rows: object, market_date: date) -> dict | None:
        if not isinstance(rows, list):
            return None
        for row in rows:
            if isinstance(row, dict) and row.get("date") == market_date.isoformat() and _valid_row(row):
                return row
        return None

    @staticmethod
    def _quote_from_row(ticker: str, row: dict, movement: Decimal | None) -> MarketQuote | None:
        try:
            price = _decimal(row.get("close", row.get("adjusted_close")))
            currency = _currency(row.get("currency") or EODHD_CURRENCIES[ticker.upper()])
            return MarketQuote(ticker, price, currency, movement, _parse_datetime(row["date"])) if price >= 0 else None
        except (ValueError, TypeError, InvalidOperation, KeyError):
            return None


def _valid_row(row: dict) -> bool:
    try:
        _decimal(row.get("close", row.get("adjusted_close")))
        date.fromisoformat(row["date"])
        return True
    except (ValueError, TypeError, InvalidOperation, KeyError):
        return False


def _decimal(value: object) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError("Missing numeric observation")
    return Decimal(str(value))


def _currency(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Missing currency")
    return value.strip().upper()


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Missing observation timestamp")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
