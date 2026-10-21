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


def test_replace_supports_edit_remove_and_reload_and_rejects_empty_invalid_future_or_duplicate_lots() -> None:
    client, session_factory = build_client()
    asset_id = create(client, name="ASML Holding", ticker="ASML", exchange="Euronext Amsterdam", asset_type="Stock", status="Owned").json()["id"]
    first = {"id": "one", "quantity": "0.333333", "purchasePrice": "100.123456", "purchaseDate": "2026-01-01"}
    assert client.put(f"/api/assets/{asset_id}/lots", json={"lots": [first]}).status_code == 200
    edited = {**first, "quantity": "1.000001", "purchasePrice": "200.000001"}
    assert client.put(f"/api/assets/{asset_id}/lots", json={"lots": [edited]}).json()["lots"][0]["purchasePrice"] == "200.000001"
    assert client.put(f"/api/assets/{asset_id}/lots", json={"lots": []}).status_code == 422
    for lots in (
        [{"id": "x", "quantity": "1.0000001", "purchasePrice": "2"}],
        [{"id": "x", "quantity": "1", "purchasePrice": "2", "purchaseDate": "2999-01-01"}],
        [{"id": "x", "quantity": "1", "purchasePrice": "2"}, {"id": "x", "quantity": "3", "purchasePrice": "4"}],
    ):
        assert client.put(f"/api/assets/{asset_id}/lots", json={"lots": lots}).status_code == 422
    with session_factory() as session:
        persisted = session.query(PurchaseLot).filter_by(asset_id=asset_id).one()
        assert persisted.quantity == Decimal("1.000001")
        assert persisted.purchase_price == Decimal("200.000001")
