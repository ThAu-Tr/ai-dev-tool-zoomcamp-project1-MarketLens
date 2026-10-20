from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.repositories.dashboard import DashboardRepository
from app.schemas import DashboardResponse
from app.services.dashboard import DashboardService


def create_app() -> FastAPI:
    app = FastAPI(title="MarketLens API", openapi_url=None)

    @app.get("/api/dashboard", response_model=DashboardResponse)
    def get_dashboard(session: Session = Depends(get_session)) -> DashboardResponse:
        try:
            return DashboardService(DashboardRepository(session)).read_dashboard()
        except RuntimeError as error:
            raise HTTPException(status_code=500, detail=str(error)) from error

    return app


app = create_app()
