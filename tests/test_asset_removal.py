from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db import Base, get_session
from app.main import create_app
from app.models import Article, Asset, ContextSummary, DemoUser, Industry, IndustryFollow, PurchaseLot


def seed_demo_user(session: Session) -> DemoUser:
    user = DemoUser(id=1, identifier="demo-user")
    session.add(user)
    session.flush()
    return user


def build_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def _asset(asset_id: str, user_id: int, ticker: str) -> Asset:
    return Asset(
        id=asset_id, user_id=user_id, name=f"{ticker} Corp", ticker=ticker, exchange="XETRA",
        asset_type="Stock", status="Owned", price=Decimal("100"), currency="EUR",
        change_percent=Decimal("1"), as_of=datetime(2026, 10, 20, tzinfo=UTC), industries=[],
    )


def test_delete_asset_removes_its_active_lots_and_context_only() -> None:
    client, session_factory = build_client()
    with session_factory.begin() as session:
        user = seed_demo_user(session)
        session.add_all([
            Industry(id="software", name="Software"),
            IndustryFollow(user_id=user.id, industry_id="software"),
        ])
        sap = _asset("sap", user.id, "SAP")
        sap.lots = [PurchaseLot(id="sap-lot", quantity=Decimal("2"), purchase_price=Decimal("90"))]
        asml = _asset("asml", user.id, "ASML")
        asml.lots = [PurchaseLot(id="asml-lot", quantity=Decimal("3"), purchase_price=Decimal("80"))]
        session.add_all([
            sap, asml,
            ContextSummary(id="sap-summary", user_id=user.id, asset_id="sap", summary="Possible SAP context.", article_ids=[]),
            ContextSummary(id="asml-summary", user_id=user.id, asset_id="asml", summary="Possible ASML context.", article_ids=[]),
            Article(id="sap-only", user_id=user.id, headline="SAP", source="Test", published_at=datetime(2026, 10, 20, tzinfo=UTC), relevance="Direct asset news", assets=["SAP"], industries=[], snippet="Stored.", url="https://example.test/sap"),
            Article(id="shared", user_id=user.id, headline="Shared", source="Test", published_at=datetime(2026, 10, 20, tzinfo=UTC), relevance="Direct asset news", assets=["SAP", "ASML"], industries=[], snippet="Stored.", url="https://example.test/shared"),
            Article(id="industry", user_id=user.id, headline="Industry", source="Test", published_at=datetime(2026, 10, 20, tzinfo=UTC), relevance="Industry news", assets=[], industries=["software"], snippet="Stored.", url="https://example.test/industry"),
        ])

    response = client.delete("/api/assets/sap")

    assert response.status_code == 204
    assert response.content == b""
    dashboard = client.get("/api/dashboard").json()
    assert [asset["id"] for asset in dashboard["assets"]] == ["asml"]
    assert dashboard["assets"][0]["lots"] == [{"id": "asml-lot", "quantity": "3.000000", "purchasePrice": "80.000000"}]
    assert [summary["assetId"] for summary in dashboard["summaries"]] == ["asml"]
    assert {article["id"]: article["assets"] for article in dashboard["articles"]} == {"shared": ["ASML"], "industry": []}

    with session_factory() as session:
        assert session.get(Asset, "sap") is None
        assert session.get(PurchaseLot, "sap-lot") is None
        assert session.scalars(select(ContextSummary).where(ContextSummary.asset_id == "sap")).first() is None


def test_delete_missing_asset_returns_not_found_without_changing_stored_data() -> None:
    client, session_factory = build_client()
    with session_factory.begin() as session:
        user = seed_demo_user(session)
        asset = _asset("asml", user.id, "ASML")
        asset.lots = [PurchaseLot(id="asml-lot", quantity=Decimal("3"), purchase_price=Decimal("80"))]
        session.add(asset)

    response = client.delete("/api/assets/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "The requested asset was not found."}
    with session_factory() as session:
        assert session.get(Asset, "asml") is not None
        assert session.get(PurchaseLot, "asml-lot") is not None
