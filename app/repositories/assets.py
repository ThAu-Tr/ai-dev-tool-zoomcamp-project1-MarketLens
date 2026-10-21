from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, Asset, ContextSummary, DemoUser


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

    def asset_for(self, *, user_id: int, asset_id: str) -> Asset | None:
        return self.session.scalar(select(Asset).where(Asset.user_id == user_id, Asset.id == asset_id))

    def remove_active_asset_context(self, asset: Asset) -> None:
        """Remove current-dashboard data only; timeline/archive records are separate."""
        self.session.query(ContextSummary).filter(
            ContextSummary.user_id == asset.user_id,
            ContextSummary.asset_id == asset.id,
        ).delete(synchronize_session=False)

        for article in self.session.scalars(select(Article).where(Article.user_id == asset.user_id)):
            if asset.ticker not in article.assets:
                continue
            if article.relevance == "Direct asset news" and article.assets == [asset.ticker]:
                self.session.delete(article)
            else:
                article.assets = [ticker for ticker in article.assets if ticker != asset.ticker]

        self.session.delete(asset)
        self.session.commit()
