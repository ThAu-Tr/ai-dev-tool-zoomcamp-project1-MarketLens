from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import create_app
from app.models import Article, Asset, ContextSummary, DemoUser, PurchaseLot, RefreshState


@pytest.fixture
def session_factory() -> sessionmaker[Session]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def build_client(session_factory: sessionmaker[Session], provider_gateway: object | None = None) -> TestClient:
    app = create_app(provider_gateway)  # type: ignore[arg-type]

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


@pytest.fixture
def client(session_factory: sessionmaker[Session]) -> TestClient:
    return build_client(session_factory)


def seed_demo_user(session: Session) -> DemoUser:
    user = DemoUser(id=1, identifier="demo-user")
    session.add(user)
    session.flush()
    return user


def test_dashboard_returns_persisted_populated_data_without_writing_or_provider_calls(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    refreshed_at = datetime(2026, 10, 20, 9, 45, tzinfo=UTC)
    with session_factory.begin() as session:
        user = seed_demo_user(session)
        asset = Asset(id="sap", user_id=user.id, name="SAP SE", ticker="SAP", exchange="XETRA", asset_type="Stock", status="Owned", price=Decimal("210.35"), currency="EUR", change_percent=Decimal("-2.30"), as_of=refreshed_at, industries=["Enterprise software", "AI"])
        asset.lots = [PurchaseLot(id="sap-1", quantity=Decimal("5"), purchase_price=Decimal("130.00")), PurchaseLot(id="sap-2", quantity=Decimal("3"), purchase_price=Decimal("150.00"))]
        session.add_all([asset, Article(id="asset-news", user_id=user.id, headline="SAP update", source="Market Wire", published_at=refreshed_at, relevance="Direct asset news", assets=["SAP"], industries=[], snippet="Stored asset news.", url="https://example.test/sap"), Article(id="industry-news", user_id=user.id, headline="Software update", source="Market Wire", published_at=refreshed_at, relevance="Industry news", assets=[], industries=["Enterprise software"], snippet="Stored industry news.", url="https://example.test/software"), Article(id="market-news", user_id=user.id, headline="Rates update", source="Market Wire", published_at=refreshed_at, relevance="Market context", assets=[], industries=[], snippet="Stored market context.", url="https://example.test/rates"), ContextSummary(id="summary-1", user_id=user.id, asset_id="sap", summary="Possible context only; verify linked reports.", article_ids=["asset-news"]), RefreshState(user_id=user.id, last_refreshed_at=refreshed_at)])

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"assets", "articles", "summaries", "lastRefreshedAt", "newsStatus"}
    assert body["assets"][0] == {"id": "sap", "name": "SAP SE", "ticker": "SAP", "exchange": "XETRA", "type": "Stock", "status": "Owned", "price": 210.35, "currency": "EUR", "changePercent": -2.3, "asOf": "2026-10-20T09:45:00Z", "lots": [{"id": "sap-1", "quantity": "5.000000", "purchasePrice": "130.000000"}, {"id": "sap-2", "quantity": "3.000000", "purchasePrice": "150.000000"}], "industries": ["Enterprise software", "AI"], "priceStatus": "current"}
    assert [article["relevance"] for article in body["articles"]] == ["Direct asset news", "Industry news", "Market context"]
    assert body["summaries"][0]["articleIds"] == ["asset-news"]
    assert body["lastRefreshedAt"] == "2026-10-20T09:45:00Z"
    assert body["newsStatus"] == "current"

    with session_factory() as session:
        # SQLite does not preserve timezone metadata; the database value must still be unchanged.
        assert session.get(RefreshState, 1).last_refreshed_at == refreshed_at.replace(tzinfo=None)
        assert session.query(Article).count() == 3


def test_dashboard_returns_empty_stored_state(client: TestClient, session_factory: sessionmaker[Session]) -> None:
    with session_factory.begin() as session:
        seed_demo_user(session)

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    assert response.json() == {"assets": [], "articles": [], "summaries": [], "lastRefreshedAt": "Not refreshed yet", "newsStatus": "current"}


def test_dashboard_read_does_not_access_any_provider(session_factory: sessionmaker[Session]) -> None:
    class FailingProviderGateway:
        calls: list[str] = []

        def fetch_market_data(self) -> None:
            self.calls.append("market")
            raise AssertionError("Dashboard reads must not fetch market data")

        def fetch_news(self) -> None:
            self.calls.append("news")
            raise AssertionError("Dashboard reads must not fetch news")

        def generate_context(self) -> None:
            self.calls.append("ai")
            raise AssertionError("Dashboard reads must not generate AI context")

    with session_factory.begin() as session:
        seed_demo_user(session)

    provider_gateway = FailingProviderGateway()
    response = build_client(session_factory, provider_gateway).get("/api/dashboard")

    assert response.status_code == 200
    assert provider_gateway.calls == []
