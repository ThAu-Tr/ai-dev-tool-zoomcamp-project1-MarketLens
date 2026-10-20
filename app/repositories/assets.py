from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Asset, DemoUser


class AssetRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def demo_user(self) -> DemoUser | None:
        return self.session.scalar(select(DemoUser).where(DemoUser.identifier == "demo-user"))

    def has_asset(self, *, user_id: int, ticker: str, exchange: str) -> bool:
        return self.session.scalar(
            select(Asset.id).where(Asset.user_id == user_id, Asset.ticker == ticker, Asset.exchange == exchange)
        ) is not None

    def add(self, asset: Asset) -> Asset:
        self.session.add(asset)
        self.session.commit()
        self.session.refresh(asset)
        return asset
