from __future__ import annotations

from datetime import UTC, datetime

from app.repositories.dashboard import DashboardRepository
from app.schemas import ArticleResponse, AssetResponse, ContextSummaryResponse, DashboardResponse, LotResponse


class DashboardService:
    """Read the persisted dashboard projection; this workflow never calls providers."""

    def __init__(self, repository: DashboardRepository) -> None:
        self.repository = repository

    def read_dashboard(self) -> DashboardResponse:
        user = self.repository.demo_user()
        if user is None:
            raise RuntimeError("The seeded demo user is missing. Run database migrations before serving requests.")

        assets = self.repository.assets_for(user.id)
        articles = self.repository.articles_for(user.id)
        summaries = self.repository.summaries_for(user.id)
        refresh_state = self.repository.refresh_state_for(user.id)

        return DashboardResponse(
            assets=[
                AssetResponse(
                    id=asset.id,
                    name=asset.name,
                    ticker=asset.ticker,
                    exchange=asset.exchange,
                    type=asset.asset_type,
                    status=asset.status,
                    price=asset.price,
                    currency=asset.currency,
                    changePercent=asset.change_percent,
                    asOf=_as_utc(asset.as_of),
                    lots=[LotResponse(id=lot.id, quantity=lot.quantity, purchasePrice=lot.purchase_price) for lot in asset.lots],
                    industries=asset.industries,
                )
                for asset in assets
            ],
            articles=[
                ArticleResponse(
                    id=article.id,
                    headline=article.headline,
                    source=article.source,
                    publishedAt=_as_utc(article.published_at),
                    relevance=article.relevance,
                    assets=article.assets,
                    industries=article.industries,
                    snippet=article.snippet,
                    url=article.url,
                )
                for article in articles
            ],
            summaries=[
                ContextSummaryResponse(
                    id=summary.id,
                    assetId=summary.asset_id,
                    summary=summary.summary,
                    articleIds=summary.article_ids,
                )
                for summary in summaries
            ],
            lastRefreshedAt=_as_utc(refresh_state.last_refreshed_at) if refresh_state and refresh_state.last_refreshed_at else None,
        )


def _as_utc(value: datetime) -> datetime:
    """Normalize database values, including SQLite test values, to an API timestamp."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
