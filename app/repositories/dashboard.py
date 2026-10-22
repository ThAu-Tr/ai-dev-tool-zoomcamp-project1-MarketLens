from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Article, Asset, ContextSummary, DemoUser, Industry, RefreshState


class DashboardRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def demo_user(self) -> DemoUser | None:
        return self.session.scalar(select(DemoUser).where(DemoUser.identifier == "demo-user"))

    def assets_for(self, user_id: int) -> list[Asset]:
        return list(
            self.session.scalars(
                select(Asset).where(Asset.user_id == user_id).options(selectinload(Asset.lots)).order_by(Asset.ticker)
            )
        )

    def articles_for(self, user_id: int) -> list[Article]:
        return list(self.session.scalars(select(Article).where(Article.user_id == user_id, Article.relevance.in_(["Direct asset news", "Industry news", "Market context"])).order_by(Article.published_at.desc())))

    def industry_names(self, industry_ids: list[str]) -> dict[str, str]:
        if not industry_ids:
            return {}
        rows = self.session.scalars(select(Industry).where(Industry.id.in_(industry_ids)))
        return {industry.id: industry.name for industry in rows}

    def summaries_for(self, user_id: int) -> list[ContextSummary]:
        return list(self.session.scalars(select(ContextSummary).where(ContextSummary.user_id == user_id).order_by(ContextSummary.id)))

    def refresh_state_for(self, user_id: int) -> RefreshState | None:
        return self.session.get(RefreshState, user_id)
