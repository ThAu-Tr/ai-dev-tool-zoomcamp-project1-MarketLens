from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import create_app
from app.models import Asset, DemoUser, Industry, IndustryFollow, PurchaseLot


def build_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))
        session.add_all([Industry(id="software", name="Enterprise software"), Industry(id="semi", name="Semiconductors"), Industry(id="ai", name="AI"), Industry(id="energy", name="Renewable energy")])

    app = create_app()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def test_industries_list_every_supported_industry_once_with_follow_state() -> None:
    client, _ = build_client()

    response = client.get("/api/industries")

    assert response.status_code == 200
    assert response.json() == [
        {"id": "ai", "name": "AI", "followed": False, "suggested": False, "assets": []},
        {"id": "software", "name": "Enterprise software", "followed": False, "suggested": False, "assets": []},
            {"id": "energy", "name": "Renewable energy", "followed": False, "suggested": False, "assets": []},
        {"id": "semi", "name": "Semiconductors", "followed": False, "suggested": False, "assets": []},
    ]
    assert len({industry["id"] for industry in response.json()}) == len(response.json())


def test_follow_and_unfollow_are_persistent_and_idempotent_without_touching_assets_or_lots() -> None:
    client, session_factory = build_client()
    with session_factory.begin() as session:
        session.add(Asset(id="asset-1", user_id=1, name="Asset", ticker="AST", exchange="X", asset_type="Stock", status="Interested", price=None, currency=None, change_percent=None, as_of=None, industries=[], lots=[]))
        session.add(PurchaseLot(id="lot-1", asset_id="asset-1", quantity=1, purchase_price=10))

    for _ in range(2):
        response = client.put("/api/industries/semi/follow", json={"followed": True})
        assert response.status_code == 200
        assert response.json() == {"id": "semi", "name": "Semiconductors", "followed": True, "suggested": False, "assets": []}
    assert next(item for item in client.get("/api/industries").json() if item["id"] == "semi")["followed"] is True

    for _ in range(2):
        response = client.put("/api/industries/semi/follow", json={"followed": False})
        assert response.status_code == 200
        assert response.json()["followed"] is False
    assert next(item for item in client.get("/api/industries").json() if item["id"] == "semi")["followed"] is False

    with session_factory() as session:
        assert list(session.scalars(select(IndustryFollow))) == []
        assert session.get(Asset, "asset-1").ticker == "AST"
        assert session.get(PurchaseLot, "lot-1").quantity == 1


def test_unknown_industry_returns_not_found_without_changing_follow_state() -> None:
    client, _ = build_client()
    client.put("/api/industries/semi/follow", json={"followed": True})

    response = client.put("/api/industries/unknown/follow", json={"followed": False})

    assert response.status_code == 404
    assert response.json()["detail"] == "The requested industry was not found."
    assert next(item for item in client.get("/api/industries").json() if item["id"] == "semi")["followed"] is True


def test_suggestions_use_stock_and_etf_metadata_deduplicate_and_exclude_indices_and_followed() -> None:
    client, session_factory = build_client()
    with session_factory.begin() as session:
        session.add_all([
            Asset(id="stock", user_id=1, name="ASML Holding", ticker="ASML", exchange="X", asset_type="Stock", status="Interested", price=None, currency=None, change_percent=None, as_of=None, industries=["Semiconductors", "Unknown"], lots=[]),
            Asset(id="etf", user_id=1, name="Clean ETF", ticker="ICLN", exchange="X", asset_type="ETF", status="Interested", price=None, currency=None, change_percent=None, as_of=None, industries=[], lots=[]),
            Asset(id="index", user_id=1, name="S&P 500", ticker="SPX", exchange="X", asset_type="Index", status="Interested", price=None, currency=None, change_percent=None, as_of=None, industries=["US equities"], lots=[]),
        ])
    client.put("/api/industries/semi/follow", json={"followed": True})

    body = client.get("/api/industries").json()
    assert next(item for item in body if item["id"] == "semi") == {"id": "semi", "name": "Semiconductors", "followed": True, "suggested": False, "assets": ["ASML"]}
    assert next(item for item in body if item["id"] == "energy") == {"id": "energy", "name": "Renewable energy", "followed": False, "suggested": True, "assets": ["ICLN"]}
    assert not any(item["suggested"] and item["name"] == "US equities" for item in body)


def test_following_suggestion_removes_it_from_suggestions_and_persists() -> None:
    client, session_factory = build_client()
    with session_factory.begin() as session:
        session.add(Asset(id="asset", user_id=1, name="ASML Holding", ticker="ASML", exchange="X", asset_type="Stock", status="Interested", price=None, currency=None, change_percent=None, as_of=None, industries=["Semiconductors"], lots=[]))
    before = next(item for item in client.get("/api/industries").json() if item["id"] == "semi")
    assert before["suggested"] is True and before["assets"] == ["ASML"]
    assert client.put("/api/industries/semi/follow", json={"followed": True}).status_code == 200
    after = next(item for item in client.get("/api/industries").json() if item["id"] == "semi")
    assert after["followed"] is True and after["suggested"] is False
