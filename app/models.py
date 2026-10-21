from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DemoUser(Base):
    __tablename__ = "demo_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(80), unique=True)


class Industry(Base):
    __tablename__ = "industries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)


class IndustryFollow(Base):
    __tablename__ = "industry_follows"

    user_id: Mapped[int] = mapped_column(ForeignKey("demo_users.id"), primary_key=True)
    industry_id: Mapped[str] = mapped_column(ForeignKey("industries.id"), primary_key=True)


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("user_id", "ticker", "exchange", name="uq_assets_user_ticker_exchange"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("demo_users.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    ticker: Mapped[str] = mapped_column(String(32))
    exchange: Mapped[str] = mapped_column(String(120))
    asset_type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    change_percent: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    as_of: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    industries: Mapped[list[str]] = mapped_column(JSON, default=list)
    lots: Mapped[list[PurchaseLot]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class PurchaseLot(Base):
    __tablename__ = "purchase_lots"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    purchase_price: Mapped[Decimal] = mapped_column(Numeric(20, 6))
    purchase_date: Mapped[date | None] = mapped_column(nullable=True)
    asset: Mapped[Asset] = relationship(back_populates="lots")


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("user_id", "url", name="uq_articles_user_url"),)

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("demo_users.id"), index=True)
    headline: Mapped[str] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    relevance: Mapped[str] = mapped_column(String(32))
    assets: Mapped[list[str]] = mapped_column(JSON, default=list)
    industries: Mapped[list[str]] = mapped_column(JSON, default=list)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(2048))


class ContextSummary(Base):
    __tablename__ = "context_summaries"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("demo_users.id"), index=True)
    asset_id: Mapped[str] = mapped_column(ForeignKey("assets.id"))
    summary: Mapped[str] = mapped_column(Text)
    article_ids: Mapped[list[str]] = mapped_column(JSON, default=list)


class RefreshState(Base):
    __tablename__ = "refresh_states"

    user_id: Mapped[int] = mapped_column(ForeignKey("demo_users.id"), primary_key=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="never")
    unavailable_tickers: Mapped[list[str]] = mapped_column(JSON, default=list)
    news_status: Mapped[str] = mapped_column(String(16), default="current")
