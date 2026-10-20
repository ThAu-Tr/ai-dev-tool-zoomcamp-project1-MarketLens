from __future__ import annotations

from uuid import uuid4

from app.models import Asset
from app.repositories.assets import AssetRepository
from app.services.catalogue import AssetCatalogueService
from app.schemas import AssetCreateRequest, AssetResponse, LotResponse


class AssetCreationService:
    def __init__(self, repository: AssetRepository, catalogue: AssetCatalogueService) -> None:
        self.repository = repository
        self.catalogue = catalogue

    def create(self, request: AssetCreateRequest) -> AssetResponse:
        if request.type == "Index" and request.status == "Owned":
            raise ValueError("Indices can only be followed as Interested.")

        entry = self.catalogue.selected_entry(
            name=request.name, ticker=request.ticker, exchange=request.exchange, asset_type=request.type
        )
        if entry is None:
            raise ValueError("Select an unchanged Stock, ETF, or Index from the supported asset catalogue.")

        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")
        if self.repository.has_asset(user_id=user.id, ticker=request.ticker, exchange=request.exchange):
            raise ValueError("This asset is already in your watchlist.")

        asset = self.repository.add(Asset(
            id=uuid4().hex,
            user_id=user.id,
            name=request.name,
            ticker=request.ticker,
            exchange=request.exchange,
            asset_type=request.type,
            status=request.status,
            price=None,
            currency=None,
            change_percent=None,
            as_of=None,
            industries=list(entry["industries"]),
            lots=[],
        ))
        return AssetResponse(
            id=asset.id, name=asset.name, ticker=asset.ticker, exchange=asset.exchange,
            type=asset.asset_type, status=asset.status, price=None, currency=None,
            changePercent=None, asOf=None, lots=[LotResponse(id=lot.id, quantity=str(lot.quantity), purchasePrice=str(lot.purchase_price)) for lot in asset.lots],
            industries=asset.industries,
        )
