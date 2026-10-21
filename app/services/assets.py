from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from app.models import Asset, PurchaseLot
from app.repositories.assets import AssetRepository
from app.services.catalogue import AssetCatalogueService
from app.schemas import AssetCreateRequest, AssetResponse, AssetUpdateRequest, LotInput, LotResponse, LotsReplaceRequest


def _lot_response(lot: PurchaseLot) -> LotResponse:
    return LotResponse(id=lot.id, quantity=f"{lot.quantity:.6f}", purchasePrice=f"{lot.purchase_price:.6f}", purchaseDate=lot.purchase_date)


def _validated_lots(asset_id: str, inputs: list[LotInput]) -> list[PurchaseLot]:
    if not inputs:
        raise ValueError("At least one active purchase lot is required when changing to Owned.")
    lots: list[PurchaseLot] = []
    seen: set[str] = set()
    try:
        for item in inputs:
            if not item.id or item.id in seen:
                raise ValueError("Lot IDs must be unique.")
            quantity, price = Decimal(item.quantity), Decimal(item.purchasePrice)
            if any(len(part.split(".", 1)[1]) > 6 for part in (item.quantity, item.purchasePrice) if "." in part):
                raise ValueError("Lot quantity and purchase price support at most 6 decimal places.")
            if not quantity.is_finite() or not price.is_finite() or quantity <= 0 or price <= 0:
                raise ValueError("Lot quantity and purchase price must be positive decimals.")
            if item.purchaseDate is not None and item.purchaseDate > date.today():
                raise ValueError("Purchase date cannot be in the future.")
            seen.add(item.id)
            lots.append(PurchaseLot(id=item.id, asset_id=asset_id, quantity=quantity, purchase_price=price, purchase_date=item.purchaseDate))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(str(error) or "Lot quantity and purchase price must be positive decimals.") from error
    return lots


class LotService:
    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository

    def replace(self, asset_id: str, request: LotsReplaceRequest) -> AssetResponse:
        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")
        asset = self.repository.asset_for(user_id=user.id, asset_id=asset_id)
        if asset is None:
            raise LookupError("The requested asset was not found.")
        if asset.asset_type == "Index":
            raise ValueError("Indices cannot have purchase lots.")
        if asset.status != "Owned":
            raise ValueError("Only owned assets can have purchase lots.")
        if not request.lots:
            raise ValueError("An owned asset must have at least one active purchase lot.")
        lots = _validated_lots(asset.id, request.lots)
        self.repository.replace_lots(asset, lots)
        return AssetResponse(id=asset.id, name=asset.name, ticker=asset.ticker, exchange=asset.exchange,
            type=asset.asset_type, status=asset.status, price=asset.price, currency=asset.currency,
            changePercent=asset.change_percent, asOf=asset.as_of, lots=[_lot_response(lot) for lot in asset.lots], industries=asset.industries)


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
            changePercent=None, asOf=None, lots=[_lot_response(lot) for lot in asset.lots],
            industries=asset.industries,
        )


class AssetOwnershipService:
    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository

    def update(self, asset_id: str, request: AssetUpdateRequest) -> AssetResponse:
        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")
        asset = self.repository.asset_for(user_id=user.id, asset_id=asset_id)
        if asset is None:
            raise LookupError("The requested asset was not found.")
        if asset.asset_type == "Index" and request.status == "Owned":
            raise ValueError("Indices can only be followed as Interested.")

        transitioning_to_owned = asset.status == "Interested" and request.status == "Owned"
        if request.lots is not None and not transitioning_to_owned:
            raise ValueError("Initial purchase lots can only be supplied when changing an Interested asset to Owned.")

        initial_lots: list[PurchaseLot] | None = None
        if transitioning_to_owned and not asset.lots:
            if request.lots is None:
                raise ValueError("At least one active purchase lot is required when changing to Owned.")
            initial_lots = _validated_lots(asset.id, request.lots)
        elif transitioning_to_owned and request.lots:
            raise ValueError("This asset already has saved purchase lots; change its status without initial lots.")
        elif transitioning_to_owned and request.lots == []:
            raise ValueError("At least one active purchase lot is required when changing to Owned.")

        updated = self.repository.update_status(asset, status=request.status, initial_lots=initial_lots)
        return AssetResponse(
            id=updated.id, name=updated.name, ticker=updated.ticker, exchange=updated.exchange,
            type=updated.asset_type, status=updated.status, price=updated.price, currency=updated.currency,
            changePercent=updated.change_percent, asOf=updated.as_of,
            lots=[_lot_response(lot) for lot in updated.lots], industries=updated.industries,
        )


class AssetRemovalService:
    def __init__(self, repository: AssetRepository) -> None:
        self.repository = repository

    def remove(self, asset_id: str) -> bool:
        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")
        asset = self.repository.asset_for(user_id=user.id, asset_id=asset_id)
        if asset is None:
            return False
        self.repository.remove_active_asset_context(asset)
        return True
