from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import create_app
from app.models import Asset, DemoUser


def build_client() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine("sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory.begin() as session:
        session.add(DemoUser(id=1, identifier="demo-user"))

    app = create_app()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app), session_factory


def create(client: TestClient, *, name: str, ticker: str, exchange: str, asset_type: str, status: str) -> object:
    return client.post("/api/assets", json={
        "name": name, "ticker": ticker, "exchange": exchange, "type": asset_type, "status": status,
    })


def test_create_stock_etf_and_index_persists_catalogue_metadata_without_a_quote() -> None:
    client, session_factory = build_client()

    stock = create(client, name="ASML Holding", ticker="ASML", exchange="Euronext Amsterdam", asset_type="Stock", status="Owned")
    etf = create(client, name="Vanguard S&P 500 ETF", ticker="VOO", exchange="NYSE Arca", asset_type="ETF", status="Interested")
    index = create(client, name="S&P 500", ticker="SPX", exchange="S&P Dow Jones Indices", asset_type="Index", status="Interested")

    for response, expected_type, expected_status in ((stock, "Stock", "Owned"), (etf, "ETF", "Interested"), (index, "Index", "Interested")):
        assert response.status_code == 201
        body = response.json()
        assert body["type"] == expected_type
        assert body["status"] == expected_status
        assert body["lots"] == []
        assert body["price"] is None
        assert body["currency"] is None
        assert body["changePercent"] is None
        assert body["asOf"] is None

    with session_factory() as session:
        assets = list(session.query(Asset).order_by(Asset.ticker))
        assert [(asset.ticker, asset.status, asset.industries) for asset in assets] == [
            ("ASML", "Owned", ["Semiconductors"]),
            ("SPX", "Interested", ["US equities"]),
            ("VOO", "Interested", ["US equities"]),
        ]


def test_create_apple_persists_catalogue_identity_and_rejects_duplicate() -> None:
    client, session_factory = build_client()
    apple = {"name": "Apple Inc.", "ticker": "AAPL", "exchange": "NASDAQ", "type": "Stock", "status": "Interested"}

    created = client.post("/api/assets", json=apple)
    duplicate = client.post("/api/assets", json=apple)

    assert created.status_code == 201
    assert {key: created.json()[key] for key in ("name", "ticker", "exchange", "type", "industries")} == {
        "name": "Apple Inc.", "ticker": "AAPL", "exchange": "NASDAQ", "type": "Stock", "industries": ["Technology hardware"],
    }
    assert created.json()["price"] is None
    assert duplicate.status_code == 422
    assert duplicate.json()["detail"] == "This asset is already in your watchlist."

    with session_factory() as session:
        apples = list(session.query(Asset).filter_by(ticker="AAPL"))
    assert len(apples) == 1


def test_create_rejects_tampered_unknown_and_duplicate_catalogue_selections() -> None:
    client, _ = build_client()
    valid = {"name": "ASML Holding", "ticker": "ASML", "exchange": "Euronext Amsterdam", "asset_type": "Stock", "status": "Interested"}

    assert create(client, **valid).status_code == 201
    duplicate = create(client, **valid)
    tampered = create(client, name="ASML Holding", ticker="ASML", exchange="NASDAQ", asset_type="Stock", status="Interested")
    unknown = create(client, name="Unknown Corp", ticker="NOPE", exchange="XETRA", asset_type="Stock", status="Interested")

    assert duplicate.status_code == 422
    assert duplicate.json()["detail"] == "This asset is already in your watchlist."
    for response in (tampered, unknown):
        assert response.status_code == 422
        assert response.json()["detail"] == "Select an unchanged Stock, ETF, or Index from the supported asset catalogue."


def test_create_rejects_an_owned_index() -> None:
    client, _ = build_client()

    response = create(client, name="S&P 500", ticker="SPX", exchange="S&P Dow Jones Indices", asset_type="Index", status="Owned")

    assert response.status_code == 422
    assert response.json()["detail"] == "Indices can only be followed as Interested."


def test_create_rejects_browser_controlled_lots_and_industries() -> None:
    client, _ = build_client()

    response = client.post("/api/assets", json={
        "name": "ASML Holding", "ticker": "ASML", "exchange": "Euronext Amsterdam", "type": "Stock", "status": "Owned",
        "lots": [{"id": "browser-lot", "quantity": "5", "purchasePrice": "10"}], "industries": ["Altered"],
    })

    assert response.status_code == 422
