from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import create_app
from app.models import Asset, DemoUser, HistoricalDay
from app.providers import MarketQuote, NewsArticle


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
    return factory


def client_for(factory: sessionmaker[Session], provider: object | None = None) -> TestClient:
    app = create_app(provider)  # type: ignore[arg-type]

    def override_session():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_asset_can_be_added_managed_and_retrieved_from_dashboard(session_factory):
    client = client_for(session_factory)

    search = client.get("/api/assets/search", params={"q": "asml"})
    assert search.status_code == 200
    selected = search.json()[0]
    added = client.post("/api/assets", json={**selected, "status": "Interested"})
    assert added.status_code == 201
    asset_id = added.json()["id"]
    managed = client.patch(f"/api/assets/{asset_id}", json={
        "status": "Owned",
        "lots": [{"id": "opening", "quantity": "1.250000", "purchasePrice": "100.100000"}],
    })
    assert managed.status_code == 200

    dashboard = client.get("/api/dashboard")

    assert dashboard.status_code == 200
    asset = dashboard.json()["assets"][0]
    assert asset["id"] == asset_id
    assert asset["status"] == "Owned"
    assert asset["lots"] == [{"id": "opening", "quantity": "1.250000", "purchasePrice": "100.100000"}]
    with session_factory() as session:
        saved = session.get(Asset, asset_id)
        assert saved is not None and saved.status == "Owned" and len(saved.lots) == 1


class RefreshGateway:
    def __init__(self, now: datetime):
        self.now = now
        self.calls: list[str] = []

    def fetch_market_data(self, tickers, since):
        self.calls.append("market")
        return [MarketQuote(tickers[0], Decimal("101.50"), "EUR", Decimal("1.50"), self.now)]

    def fetch_news(self, tickers, since, industries=None):
        self.calls.append("news")
        return [NewsArticle(
            "SAP expands cloud services", "Stored Wire", self.now - timedelta(minutes=10),
            "https://news.test/sap", [tickers[0]], snippet="SAP expands cloud services.",
        )]

    def generate_context(self, task, evidence):
        self.calls.append(task)
        assert task == "summarize"
        asset = evidence["assets"][0]
        return {"summaries": [{"asset_id": asset["id"], "article_ids": [asset["articles"][0]["id"]]}]}


def test_refresh_persists_price_news_and_ai_context_for_dashboard(session_factory):
    with session_factory.begin() as session:
        session.add(Asset(
            id="sap", user_id=1, name="SAP SE", ticker="SAP", exchange="XETRA", asset_type="Stock",
            status="Owned", price=Decimal("100"), currency="EUR", change_percent=Decimal("0"),
            as_of=None, industries=[],
        ))
    now = datetime.now(UTC).replace(microsecond=0)
    provider = RefreshGateway(now)
    client = client_for(session_factory, provider)

    refresh = client.post("/api/refresh")
    dashboard = client.get("/api/dashboard")

    assert refresh.status_code == 200
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["assets"][0]["price"] == 101.5
    assert body["articles"][0]["headline"] == "SAP expands cloud services"
    assert body["summaries"][0]["assetId"] == "sap"
    assert body["summaries"][0]["articleIds"] == [body["articles"][0]["id"]]
    assert provider.calls == ["market", "news", "summarize"]


class HistoryGateway:
    def __init__(self, result=None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[tuple[list[str], date]] = []

    def fetch_historical_data(self, tickers, market_date):
        self.calls.append((tickers, market_date))
        if self.error:
            raise self.error
        return self.result


def add_timeline_assets(factory: sessionmaker[Session]) -> None:
    with factory.begin() as session:
        session.add(Asset(
            id="sap", user_id=1, name="SAP SE", ticker="SAP", exchange="XETRA", asset_type="Stock",
            status="Owned", price=Decimal("123"), currency="EUR", change_percent=Decimal("1"),
            as_of=None, industries=[],
        ))


def test_historical_day_is_cached_and_revisited_without_provider_refetch(session_factory):
    add_timeline_assets(session_factory)
    market_day = date.today() - timedelta(days=1)
    quote_time = datetime.combine(market_day, datetime.min.time().replace(hour=16), tzinfo=UTC)
    provider = HistoryGateway([MarketQuote("SAP", Decimal("111.25"), "EUR", Decimal("2.5"), quote_time)])
    client = client_for(session_factory, provider)

    first = client.get("/api/timeline", params={"date": market_day.isoformat()})
    second = client.get("/api/timeline", params={"date": market_day.isoformat()})

    assert first.status_code == second.status_code == 200
    assert first.json()["source"] == "newly-loaded"
    assert second.json()["source"] == "archive"
    assert second.json()["assets"][0]["price"] == 111.25
    assert provider.calls == [(["SAP"], market_day)]


def test_historical_provider_failure_does_not_persist_an_archive(session_factory):
    add_timeline_assets(session_factory)
    market_day = date.today() - timedelta(days=2)
    provider = HistoryGateway(error=TimeoutError("offline"))

    response = client_for(session_factory, provider).get("/api/timeline", params={"date": market_day.isoformat()})

    assert response.status_code == 502
    with session_factory() as session:
        assert session.scalar(select(HistoricalDay)) is None
    assert provider.calls == [(["SAP"], market_day)]
