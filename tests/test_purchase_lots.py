from decimal import Decimal

from tests.test_asset_creation import build_client, create
from app.models import Asset, PurchaseLot


def test_replace_lots_validates_authorization_dates_and_replaces_atomically() -> None:
    client, session_factory = build_client()
    response = create(client, name="ASML Holding", ticker="ASML", exchange="Euronext Amsterdam", asset_type="Stock", status="Owned")
    asset_id = response.json()["id"]
    saved = client.put(f"/api/assets/{asset_id}/lots", json={"lots": [{"id": "lot-1", "quantity": "1.25", "purchasePrice": "100.10", "purchaseDate": "2026-10-20"}]})
    assert saved.status_code == 200
    assert saved.json()["lots"][0]["purchaseDate"] == "2026-10-20"
    assert saved.json()["lots"][0]["quantity"] == "1.250000"
    invalid = client.put(f"/api/assets/{asset_id}/lots", json={"lots": [{"id": "bad", "quantity": "0", "purchasePrice": "5"}]})
    assert invalid.status_code == 422
    with session_factory() as session:
        lots = session.query(PurchaseLot).filter_by(asset_id=asset_id).all()
        assert [(lot.id, lot.quantity) for lot in lots] == [("lot-1", Decimal("1.250000"))]


def test_lots_reject_interested_assets_and_indices() -> None:
    client, _ = build_client()
    interested = create(client, name="Vanguard S&P 500 ETF", ticker="VOO", exchange="NYSE Arca", asset_type="ETF", status="Interested").json()["id"]
    assert client.put(f"/api/assets/{interested}/lots", json={"lots": [{"id": "x", "quantity": "1", "purchasePrice": "2"}]}).status_code == 422
    index = create(client, name="S&P 500", ticker="SPX", exchange="S&P Dow Jones Indices", asset_type="Index", status="Interested").json()["id"]
    assert client.put(f"/api/assets/{index}/lots", json={"lots": [{"id": "x", "quantity": "1", "purchasePrice": "2"}]}).status_code == 422
