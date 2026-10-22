from __future__ import annotations

from typing import Annotated
from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.db import get_session
from app.providers import ProviderGateway
from app.repositories.catalogue import AssetCatalogueRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.assets import AssetRepository
from app.repositories.industries import IndustryRepository
from app.schemas import AssetCreateRequest, AssetResponse, AssetSearchResult, AssetUpdateRequest, DashboardResponse, IndustryFollowRequest, IndustryResponse, LotsReplaceRequest
from app.services.assets import AssetCreationService, AssetOwnershipService, AssetRemovalService, LotService
from app.schemas import RefreshResponse
from app.services.catalogue import AssetCatalogueService
from app.services.dashboard import DashboardService
from app.services.industries import IndustryService
from app.repositories.refresh import RefreshRepository
from app.services.refresh import ProviderUnavailableError, RefreshService
from app.repositories.timeline import TimelineRepository
from app.services.timeline import HistoricalDateOutOfRange, HistoricalProviderError, TimelineService
from app.schemas import TimelineDayResponse


def create_app(provider_gateway: ProviderGateway | None = None) -> FastAPI:
    app = FastAPI(title="MarketLens API", openapi_url=None)

    @app.get("/api/dashboard", response_model=DashboardResponse)
    def get_dashboard(session: Session = Depends(get_session)) -> DashboardResponse:
        try:
            return DashboardService(DashboardRepository(session), provider_gateway).read_dashboard()
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.get("/api/timeline", response_model=TimelineDayResponse)
    def get_timeline(date: Annotated[date, Query(description="Requested market day in YYYY-MM-DD format")], session: Session = Depends(get_session)) -> TimelineDayResponse:
        try:
            return TimelineService(TimelineRepository(session), provider_gateway).get_day(date)
        except HistoricalDateOutOfRange as error:
            raise HTTPException(status_code=403, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except HistoricalProviderError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.post("/api/refresh", response_model=RefreshResponse)
    def refresh(session: Session = Depends(get_session)) -> RefreshResponse:
        try:
            return RefreshService(RefreshRepository(session), provider_gateway).refresh()
        except ProviderUnavailableError as error:
            session.rollback()
            raise HTTPException(status_code=502, detail=str(error)) from error
        except RuntimeError as error:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.delete("/api/assets/{asset_id}", status_code=204)
    def delete_asset(asset_id: str, session: Session = Depends(get_session)) -> Response:
        try:
            removed = AssetRemovalService(AssetRepository(session)).remove(asset_id)
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        if not removed:
            raise HTTPException(status_code=404, detail="The requested asset was not found.")
        return Response(status_code=204)

    @app.get("/api/assets/search", response_model=list[AssetSearchResult])
    def search_assets(q: Annotated[str, Query(min_length=1)]) -> list[AssetSearchResult]:
        try:
            return AssetCatalogueService(AssetCatalogueRepository()).search(q)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/assets", response_model=AssetResponse, status_code=201)
    def create_asset(request: AssetCreateRequest, session: Session = Depends(get_session)) -> AssetResponse:
        try:
            return AssetCreationService(
                AssetRepository(session), AssetCatalogueService(AssetCatalogueRepository())
            ).create(request)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.put("/api/assets/{asset_id}/lots", response_model=AssetResponse)
    def replace_lots(asset_id: str, request: LotsReplaceRequest, session: Session = Depends(get_session)) -> AssetResponse:
        try:
            return LotService(AssetRepository(session)).replace(asset_id, request)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.patch("/api/assets/{asset_id}", response_model=AssetResponse)
    def update_asset(asset_id: str, request: AssetUpdateRequest, session: Session = Depends(get_session)) -> AssetResponse:
        try:
            return AssetOwnershipService(AssetRepository(session)).update(asset_id, request)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            session.rollback()
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            session.rollback()
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.get("/api/industries", response_model=list[IndustryResponse])
    def list_industries(session: Session = Depends(get_session)) -> list[IndustryResponse]:
        try:
            return IndustryService(IndustryRepository(session), AssetCatalogueRepository()).list()
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    @app.put("/api/industries/{industry_id}/follow", response_model=IndustryResponse)
    def set_industry_follow_state(industry_id: str, request: IndustryFollowRequest, session: Session = Depends(get_session)) -> IndustryResponse:
        try:
            industry = IndustryService(IndustryRepository(session)).set_followed(industry_id, request.followed)
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error
        if industry is None:
            raise HTTPException(status_code=404, detail="The requested industry was not found.")
        return industry

    return app


app = create_app()
