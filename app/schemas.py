from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_serializer


class ApiModel(BaseModel):
    @field_serializer("*", check_fields=False, when_used="json")
    def serialize_decimal(self, value: object) -> object:
        return float(value) if isinstance(value, Decimal) else value


class LotResponse(ApiModel):
    id: str
    quantity: Decimal
    purchasePrice: Decimal


class AssetResponse(ApiModel):
    id: str
    name: str
    ticker: str
    exchange: str
    type: Literal["Stock", "ETF", "Index"]
    status: Literal["Owned", "Interested"]
    price: Decimal
    currency: str
    changePercent: Decimal
    asOf: datetime
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
    lastRefreshedAt: datetime | None
