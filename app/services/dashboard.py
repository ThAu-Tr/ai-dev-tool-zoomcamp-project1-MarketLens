from __future__ import annotations

from datetime import UTC, datetime

from app.repositories.dashboard import DashboardRepository
from app.schemas import ArticleResponse, AssetResponse, ContextSummaryResponse, DashboardResponse, LotResponse
from app.providers import ProviderGateway


class DashboardService:
    """Read the persisted dashboard projection; this workflow never calls providers."""

    def __init__(self, repository: DashboardRepository, providers: ProviderGateway | None = None) -> None:
        self.repository = repository
        # Kept only as an explicit architectural boundary. read_dashboard must not access it.
        self._providers = providers

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
                    asOf=_as_utc(asset.as_of) if asset.as_of else None,
                    lots=[LotResponse(id=lot.id, quantity=_decimal_text(lot.quantity), purchasePrice=_decimal_text(lot.purchase_price), purchaseDate=lot.purchase_date) for lot in asset.lots],
                    industries=asset.industries,
                    priceStatus=("unavailable" if refresh_state and asset.ticker.upper() in (refresh_state.unavailable_tickers or []) else (refresh_state.status if refresh_state and refresh_state.status != "never" else ("current" if asset.price is not None and asset.as_of is not None else "never"))),
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
            lastRefreshedAt=_timestamp_text(refresh_state.last_refreshed_at) if refresh_state and refresh_state.last_refreshed_at else "Not refreshed yet",
            newsStatus=refresh_state.news_status if refresh_state else "current",
        )


def _as_utc(value: datetime) -> datetime:
    """Normalize database values, including SQLite test values, to an API timestamp."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _timestamp_text(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _decimal_text(value: object) -> str:
    return format(value, "f")
