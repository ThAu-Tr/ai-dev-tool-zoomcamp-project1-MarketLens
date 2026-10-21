from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, Asset, DemoUser, RefreshState
from app.providers import MarketQuote, NewsArticle


class RefreshRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def demo_user(self) -> DemoUser | None:
        return self.session.scalar(select(DemoUser).where(DemoUser.identifier == "demo-user"))

    def assets_for(self, user_id: int) -> list[Asset]:
        return list(self.session.scalars(select(Asset).where(Asset.user_id == user_id).order_by(Asset.ticker)))

    def last_refreshed_at(self, user_id: int) -> datetime | None:
        state = self.session.get(RefreshState, user_id)
        return state.last_refreshed_at if state else None

    def newest_article_at(self, user_id: int) -> datetime | None:
        return self.session.scalar(select(Article.published_at).where(Article.user_id == user_id).order_by(Article.published_at.desc()).limit(1))

    def mark_news_status(self, user_id: int, status: str) -> None:
        state = self.session.get(RefreshState, user_id)
        if state is None:
            state = RefreshState(user_id=user_id)
            self.session.add(state)
        state.news_status = status

    def save_direct_article(self, user_id: int, article: NewsArticle, article_id: str, url: str, tickers: list[str]) -> None:
        existing = self.session.scalar(select(Article).where(Article.user_id == user_id, (Article.id == article_id) | (Article.url == url)))
        if existing is not None:
            existing.assets = sorted(set(existing.assets).union(tickers))
            return
        self.session.add(Article(id=article_id, user_id=user_id, headline=article.headline, source=article.source, published_at=article.published_at, relevance="Direct asset news", assets=sorted(tickers), industries=[], snippet=article.snippet, url=url))

    def mark_unavailable(self, user_id: int, tickers: list[str]) -> None:
        state = self.session.get(RefreshState, user_id)
        if state is None:
            state = RefreshState(user_id=user_id)
            self.session.add(state)
        state.status = "unavailable"
        state.unavailable_tickers = tickers

    def apply_quotes(self, user_id: int, quotes: list[MarketQuote], refreshed_at: datetime) -> None:
        assets = {asset.ticker.upper(): asset for asset in self.assets_for(user_id)}
        for quote in quotes:
            asset = assets.get(quote.ticker.upper())
            if asset is None or quote.price < Decimal("0"):
                continue
            asset.price = quote.price
            asset.currency = quote.currency
            asset.change_percent = quote.change_percent
            asset.as_of = quote.as_of
        state = self.session.get(RefreshState, user_id)
        if state is None:
            state = RefreshState(user_id=user_id, last_refreshed_at=refreshed_at, status="current")
            self.session.add(state)
        else:
            state.last_refreshed_at = refreshed_at
            state.status = "current"
            state.unavailable_tickers = []
