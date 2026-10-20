from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.providers import ProviderGateway
from app.repositories.catalogue import AssetCatalogueRepository
from app.repositories.dashboard import DashboardRepository
from app.repositories.assets import AssetRepository
from app.schemas import AssetCreateRequest, AssetResponse, AssetSearchResult, DashboardResponse
from app.services.assets import AssetCreationService
from app.services.catalogue import AssetCatalogueService
from app.services.dashboard import DashboardService


def create_app(provider_gateway: ProviderGateway | None = None) -> FastAPI:
    app = FastAPI(title="MarketLens API", openapi_url=None)

    @app.get("/api/dashboard", response_model=DashboardResponse)
    def get_dashboard(session: Session = Depends(get_session)) -> DashboardResponse:
        try:
            return DashboardService(DashboardRepository(session), provider_gateway).read_dashboard()
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

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

    return app


app = create_app()
