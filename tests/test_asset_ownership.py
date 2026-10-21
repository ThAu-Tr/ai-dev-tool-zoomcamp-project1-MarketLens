from decimal import Decimal

from app.models import Asset, PurchaseLot
from tests.test_asset_creation import build_client, create


def test_status_transition_adds_initial_lots_atomically_and_persists_after_reload() -> None:
    client, session_factory = build_client()
    asset_id = create(client, name="Vanguard S&P 500 ETF", ticker="VOO", exchange="NYSE Arca", asset_type="ETF", status="Interested").json()["id"]

    missing = client.patch(f"/api/assets/{asset_id}", json={"status": "Owned"})
    assert missing.status_code == 422
    invalid = client.patch(f"/api/assets/{asset_id}", json={"status": "Owned", "lots": [{"id": "bad", "quantity": "0", "purchasePrice": "10"}]})
    assert invalid.status_code == 422
    saved = client.patch(f"/api/assets/{asset_id}", json={"status": "Owned", "lots": [{"id": "opening", "quantity": "2.500000", "purchasePrice": "100.250000"}]})

    assert saved.status_code == 200
    assert saved.json()["status"] == "Owned"
    assert saved.json()["lots"] == [{"id": "opening", "quantity": "2.500000", "purchasePrice": "100.250000"}]
    with session_factory() as session:
        asset = session.get(Asset, asset_id)
        assert asset is not None and asset.status == "Owned"
        assert [(lot.id, lot.quantity, lot.purchase_price) for lot in asset.lots] == [("opening", Decimal("2.500000"), Decimal("100.250000"))]


def test_status_transitions_preserve_lots_and_allow_reuse_without_initial_lots() -> None:
    client, session_factory = build_client()
    asset_id = create(client, name="ASML Holding", ticker="ASML", exchange="Euronext Amsterdam", asset_type="Stock", status="Owned").json()["id"]
    assert client.put(f"/api/assets/{asset_id}/lots", json={"lots": [{"id": "saved", "quantity": "3", "purchasePrice": "80"}]}).status_code == 200

    interested = client.patch(f"/api/assets/{asset_id}", json={"status": "Interested"})
    assert interested.status_code == 200
    assert interested.json()["lots"][0]["id"] == "saved"
    owned_again = client.patch(f"/api/assets/{asset_id}", json={"status": "Owned"})
    assert owned_again.status_code == 200
    assert owned_again.json()["lots"][0]["id"] == "saved"
    with session_factory() as session:
        assert session.query(PurchaseLot).filter_by(asset_id=asset_id).count() == 1


def test_ownership_rejects_indices_unknown_assets_and_invalid_lot_changes_without_mutation() -> None:
    client, session_factory = build_client()
    index_id = create(client, name="S&P 500", ticker="SPX", exchange="S&P Dow Jones Indices", asset_type="Index", status="Interested").json()["id"]
    assert client.patch("/api/assets/missing", json={"status": "Owned"}).status_code == 404
    assert client.patch(f"/api/assets/{index_id}", json={"status": "Owned"}).status_code == 422
    assert client.patch(f"/api/assets/{index_id}", json={"status": "Interested", "lots": []}).status_code == 422
    with session_factory() as session:
        index = session.get(Asset, index_id)
        assert index is not None and index.status == "Interested" and index.lots == []


def test_no_op_owned_update_keeps_legacy_zero_lot_asset_valid() -> None:
    client, _ = build_client()
    asset_id = create(client, name="ASML Holding", ticker="ASML", exchange="Euronext Amsterdam", asset_type="Stock", status="Owned").json()["id"]
    response = client.patch(f"/api/assets/{asset_id}", json={"status": "Owned"})
    assert response.status_code == 200
    assert response.json()["lots"] == []
