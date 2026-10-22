from datetime import date, datetime, UTC
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Asset, DemoUser, HistoricalDay, HistoricalPrice
from app.providers import MarketDataResult, MarketQuote
from tests.test_dashboard import build_client


def make_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
        session.add_all([
            Asset(id="sap", user_id=1, name="SAP SE", ticker="SAP", exchange="XETRA", asset_type="Stock", status="Owned", price=Decimal("123"), currency="EUR", change_percent=Decimal("1"), as_of=None, industries=[], lots=[]),
            Asset(id="msft", user_id=1, name="Microsoft", ticker="MSFT", exchange="NASDAQ", asset_type="Stock", status="Interested", price=Decimal("400"), currency="USD", change_percent=Decimal("1"), as_of=None, industries=[], lots=[]),
        ])
    return factory


class HistoryProvider:
    def __init__(self, result=None, error=None): self.result, self.error, self.calls = result, error, []
    def fetch_historical_data(self, tickers, market_date):
        self.calls.append((tickers, market_date))
        if self.error: raise self.error
        return self.result


def test_first_request_persists_historical_quotes_without_changing_live_quotes():
    factory = make_factory()
    provider = HistoryProvider([MarketQuote("SAP", Decimal("111.123456"), "EUR", Decimal("2.5"), datetime(2026, 10, 20, 16, tzinfo=UTC))])
    client = build_client(factory, provider)
    response = client.get("/api/timeline?date=2026-10-20")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "newly-loaded" and body["date"] == "2026-10-20"
    assert next(asset for asset in body["assets"] if asset["ticker"] == "SAP")["price"] == 111.123456
    assert next(asset for asset in body["assets"] if asset["ticker"] == "MSFT")["price"] is None
    assert body["articles"] == [] and body["summaries"] == []
    with factory() as session:
        assert session.get(Asset, "sap").price == Decimal("123.000000")
        assert session.scalar(select(HistoricalDay)).market_date == date(2026, 10, 20)
        assert session.scalar(select(HistoricalPrice).where(HistoricalPrice.ticker == "SAP")).price == Decimal("111.123456")


def test_archive_read_skips_provider_and_is_allowed_after_window():
    factory = make_factory()
    provider = HistoryProvider([])
    with factory.begin() as session:
        session.add(HistoricalDay(user_id=1, market_date=date(2026, 9, 1), market_closed=False))
        session.add(HistoricalPrice(id="archived-sap", user_id=1, market_date=date(2026, 9, 1), asset_id="sap", ticker="SAP", name="SAP SE", exchange="XETRA", asset_type="Stock", status="Owned", price=Decimal("100"), currency="EUR", change_percent=None, as_of=datetime(2026, 9, 1, tzinfo=UTC), industries=[]))
    client = build_client(factory, provider)
    response = client.get("/api/timeline?date=2026-09-01")
    assert response.status_code == 200 and response.json()["source"] == "archive"
    assert len(provider.calls) == 0


def test_invalid_future_and_outside_window_rejected_without_provider_calls():
    factory = make_factory(); provider = HistoryProvider([]); client = build_client(factory, provider)
    assert client.get("/api/timeline?date=bad").status_code == 422
    assert client.get("/api/timeline?date=2026-10-23").status_code == 400
    assert client.get("/api/timeline?date=2026-09-01").status_code == 403
    assert provider.calls == []
    with factory() as session: assert session.scalar(select(HistoricalDay)) is None


def test_empty_market_day_is_archived_but_provider_failure_is_not():
    factory = make_factory(); provider = HistoryProvider(MarketDataResult([], market_closed=True)); client = build_client(factory, provider)
    response = client.get("/api/timeline?date=2026-10-19")
    assert response.status_code == 200 and response.json()["marketClosed"] is True
    provider.error = TimeoutError("offline")
    response = client.get("/api/timeline?date=2026-10-18")
    assert response.status_code == 502
    with factory() as session:
        assert session.get(HistoricalDay, (1, date(2026, 10, 18))) is None
