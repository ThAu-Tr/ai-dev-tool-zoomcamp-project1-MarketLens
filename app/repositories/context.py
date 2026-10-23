from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import or_, select, update

from app.models import Article, ContextSummary, RefreshState
from app.repositories.refresh import RefreshRepository


class ContextRepository(RefreshRepository):
    """Persisted evidence and atomic, restart-safe demo budget checkpoint."""

    def ai_asset_cursor(self, user_id: int) -> str | None:
        state = self.session.get(RefreshState, user_id)
        return state.ai_asset_cursor if state else None

    def set_ai_status(self, user_id: int, status: str, cursor: str | None = None) -> None:
        state = self.session.get(RefreshState, user_id)
        if state is None:
            state = RefreshState(user_id=user_id)
            self.session.add(state)
        state.ai_status = status
        if cursor is not None:
            state.ai_asset_cursor = cursor
        self.session.commit()

    def claim_budget(self, user_id: int, now: datetime) -> bool:
        state = self.session.get(RefreshState, user_id)
        if state is None:
            self.session.add(RefreshState(user_id=user_id))
            self.session.flush()
        result = self.session.execute(update(RefreshState).where(
            RefreshState.user_id == user_id,
            or_(RefreshState.ai_checked_at.is_(None), RefreshState.ai_checked_at <= now - timedelta(hours=1)),
        ).values(ai_checked_at=now).execution_options(synchronize_session=False))
        self.session.commit()
        return result.rowcount == 1

    def articles_for(self, user_id: int, since: datetime, *, ambiguous: bool = False) -> list[Article]:
        categories = ["Unclassified"] if ambiguous else ["Direct asset news", "Industry news", "Market context"]
        return list(self.session.scalars(select(Article).where(
            Article.user_id == user_id, Article.relevance.in_(categories), Article.published_at >= since,
        ).order_by(Article.published_at.desc(), Article.id).limit(5 if ambiguous else 12)))

    def classify_article(self, article: Article, relevance: str, assets: list[str], industries: list[str]) -> None:
        # A concurrent deterministic refresh may have promoted this candidate
        # while the AI request was in flight. Never overwrite that classification.
        self.session.execute(update(Article).where(
            Article.id == article.id, Article.user_id == article.user_id, Article.relevance == "Unclassified",
        ).values(relevance=relevance, assets=assets, industries=industries).execution_options(synchronize_session="fetch"))
        self.session.expire(article)

    def summaries_for(self, user_id: int, asset_id: str) -> list[ContextSummary]:
        return list(self.session.scalars(select(ContextSummary).where(
            ContextSummary.user_id == user_id, ContextSummary.asset_id == asset_id,
        )))

    def save_summary(self, user_id: int, asset_id: str, summary_id: str, text: str, article_ids: list[str]) -> None:
        previous = self.summaries_for(user_id, asset_id)
        for row in previous:
            self.session.delete(row)
        self.session.add(ContextSummary(id=summary_id, user_id=user_id, asset_id=asset_id,
                                        summary=text, article_ids=article_ids))
