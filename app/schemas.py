from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_serializer


class ApiModel(BaseModel):
    @field_serializer("*", check_fields=False, when_used="json")
    def serialize_decimal(self, value: object) -> object:
        return float(value) if isinstance(value, Decimal) else value


class LotResponse(ApiModel):
    id: str
    quantity: str
    purchasePrice: str


class AssetResponse(ApiModel):
    id: str
    name: str
    ticker: str
    exchange: str
    type: Literal["Stock", "ETF", "Index"]
    status: Literal["Owned", "Interested"]
    price: Decimal | None
    currency: str | None
    changePercent: Decimal | None
    asOf: datetime | None
    lots: list[LotResponse]
    industries: list[str]


class ArticleResponse(ApiModel):
    id: str
    headline: str
    source: str
    publishedAt: datetime
    relevance: Literal["Direct asset news", "Industry news", "Market context"]
    assets: list[str]
    industries: list[str]
    snippet: str
    url: str


class ContextSummaryResponse(ApiModel):
    id: str
    assetId: str
    summary: str
    articleIds: list[str]


class DashboardResponse(ApiModel):

    assets: list[AssetResponse]
    articles: list[ArticleResponse]
    summaries: list[ContextSummaryResponse]
    lastRefreshedAt: str


class AssetSearchResult(ApiModel):
    name: str
    ticker: str
    exchange: str
    type: Literal["Stock", "ETF", "Index"]


class AssetCreateRequest(ApiModel):
    """A catalogue selection. Industries and quote values are server-owned."""

    model_config = ConfigDict(extra="forbid")

    name: str
    ticker: str
    exchange: str
    type: Literal["Stock", "ETF", "Index"]
    status: Literal["Owned", "Interested"]


class IndustryResponse(ApiModel):
    id: str
    name: str
    followed: bool
    suggested: bool = False
    assets: list[str] = []


class IndustryFollowRequest(ApiModel):
    model_config = ConfigDict(extra="forbid")

    followed: bool
