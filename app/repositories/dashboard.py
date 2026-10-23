from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Article, Asset, ContextSummary, DemoUser, Industry, IndustryFollow, RefreshState


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
        articles = list(
            self.session.scalars(
                select(Article)
                .where(Article.user_id == user_id, Article.relevance.in_(["Direct asset news", "Industry news", "Market context"]))
                .order_by(Article.published_at.desc())
            )
        )
        if not articles:
            return []

        followed_industries = set(
            self.session.scalars(select(IndustryFollow.industry_id).where(IndustryFollow.user_id == user_id))
        )
        current_tickers = {
            ticker.upper()
            for ticker in self.session.scalars(select(Asset.ticker).where(Asset.user_id == user_id))
        }

        # Articles are a persisted pool. Apply current follow state only to the
        # dashboard projection, so unfollowing never destroys articles and
        # following again can make eligible records visible immediately.
        return [
            article
            for article in articles
            if article.relevance == "Market context"
            or any(ticker.upper() in current_tickers for ticker in (article.assets or []))
            or (article.relevance == "Industry news" and bool(followed_industries.intersection(article.industries or [])))
        ]

    def industry_names(self, industry_ids: list[str]) -> dict[str, str]:
        if not industry_ids:
            return {}
        rows = self.session.scalars(select(Industry).where(Industry.id.in_(industry_ids)))
        return {industry.id: industry.name for industry in rows}

    def summaries_for(self, user_id: int) -> list[ContextSummary]:
        return list(self.session.scalars(select(ContextSummary).where(ContextSummary.user_id == user_id).order_by(ContextSummary.id)))

    def refresh_state_for(self, user_id: int) -> RefreshState | None:
        return self.session.get(RefreshState, user_id)
