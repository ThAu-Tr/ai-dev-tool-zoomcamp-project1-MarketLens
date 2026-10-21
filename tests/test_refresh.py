from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.models import Asset, DemoUser, RefreshState
from app.providers import MarketDataResult, MarketQuote
from tests.test_dashboard import build_client


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


class FakeMarketProvider:
    def __init__(self, quotes: list[MarketQuote] | None = None, error: Exception | None = None) -> None:
        self.quotes = quotes or []
        self.error = error
        self.calls: list[tuple[list[str], datetime | None]] = []

    def fetch_market_data(self, tickers: list[str], since: datetime | None) -> list[MarketQuote]:
        self.calls.append((tickers, since))
        if self.error:
            raise self.error
        return self.quotes


def seed_asset(session_factory, *, price: Decimal | None = Decimal("100")) -> None:
    with session_factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
        session.add(Asset(id="sap", user_id=1, name="SAP", ticker="SAP", exchange="XETRA", asset_type="Stock", status="Owned", price=price, currency="EUR", change_percent=Decimal("1"), as_of=datetime(2026, 10, 20, 9, tzinfo=UTC), industries=[]))


def test_refresh_updates_newer_quotes_and_passes_watermark(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider([MarketQuote("SAP", Decimal("110.25"), "EUR", Decimal("10.25"), datetime(2026, 10, 21, 9, tzinfo=UTC))])
    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        asset = session.get(Asset, "sap")
        assert asset.price == Decimal("110.250000")
        assert asset.change_percent == Decimal("10.250000")
        assert session.get(RefreshState, 1).last_refreshed_at is not None
    assert provider.calls == [(["SAP"], None)]


def test_refresh_reuses_values_when_provider_returns_no_newer_quote(session_factory):
    seed_asset(session_factory)
    with session_factory.begin() as session:
        session.add(RefreshState(user_id=1, last_refreshed_at=datetime(2026, 10, 21, 9)))
    provider = FakeMarketProvider([MarketQuote("SAP", Decimal("90"), "EUR", Decimal("-10"), datetime(2026, 10, 20, 9, tzinfo=UTC))])
    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 200
    with session_factory() as session:
        assert session.get(Asset, "sap").price == Decimal("100.000000")
    assert provider.calls[0][1] == datetime(2026, 10, 21, 9)


def test_refresh_preserves_values_when_provider_fails(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider(error=TimeoutError("offline"))
    response = build_client(session_factory, provider).post("/api/refresh")

    assert response.status_code == 502
    with session_factory() as session:
        assert session.get(Asset, "sap").price == Decimal("100.000000")
        assert session.get(RefreshState, 1).status == "unavailable"


def test_incomplete_provider_result_is_unavailable_and_does_not_write(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider()
    provider.fetch_market_data = lambda tickers, since: MarketDataResult([], ["SAP"])  # type: ignore[method-assign]
    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 502
    with session_factory() as session:
        assert session.get(Asset, "sap").price == Decimal("100.000000")
        assert session.get(RefreshState, 1).status == "unavailable"


def test_omitted_symbol_in_list_result_is_unavailable(session_factory):
    seed_asset(session_factory)
    provider = FakeMarketProvider([MarketQuote("OTHER", Decimal("4"), "EUR", Decimal("1"), datetime(2026, 10, 21, 10, tzinfo=UTC))])
    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 502
    with session_factory() as session:
        state = session.get(RefreshState, 1)
        assert state.status == "unavailable"
        assert state.unavailable_tickers == ["SAP"]


def test_no_newer_repeat_does_not_advance_watermark(session_factory):
    seed_asset(session_factory)
    watermark = datetime(2026, 10, 21, 9)
    with session_factory.begin() as session:
        session.add(RefreshState(user_id=1, last_refreshed_at=watermark))
    response = build_client(session_factory, FakeMarketProvider([])).post("/api/refresh")
    assert response.status_code == 200
    with session_factory() as session:
        assert session.get(RefreshState, 1).last_refreshed_at == watermark


def test_watermark_uses_latest_successful_quote_time(session_factory):
    seed_asset(session_factory)
    quote_time = datetime(2026, 10, 21, 12, tzinfo=UTC)
    provider = FakeMarketProvider([MarketQuote("SAP", Decimal("110"), "EUR", Decimal("10"), quote_time)])
    response = build_client(session_factory, provider).post("/api/refresh")
    assert response.status_code == 200
    assert response.json()["lastRefreshedAt"] == "2026-10-21T12:00:00Z"
    with session_factory() as session:
        assert session.get(RefreshState, 1).last_refreshed_at == quote_time.replace(tzinfo=None)
