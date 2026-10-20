"""Create persisted dashboard data and seed the demo user.

Revision ID: 20261020_01
Revises:
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20261020_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("demo_users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("identifier", sa.String(length=80), nullable=False, unique=True))
    op.create_table("assets", sa.Column("id", sa.String(length=80), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("demo_users.id"), nullable=False), sa.Column("name", sa.String(length=255), nullable=False), sa.Column("ticker", sa.String(length=32), nullable=False), sa.Column("exchange", sa.String(length=120), nullable=False), sa.Column("asset_type", sa.String(length=16), nullable=False), sa.Column("status", sa.String(length=16), nullable=False), sa.Column("price", sa.Numeric(20, 6), nullable=False), sa.Column("currency", sa.String(length=8), nullable=False), sa.Column("change_percent", sa.Numeric(12, 6), nullable=False), sa.Column("as_of", sa.DateTime(timezone=True), nullable=False), sa.Column("industries", sa.JSON(), nullable=False))
    op.create_index("ix_assets_user_id", "assets", ["user_id"])
    op.create_table("purchase_lots", sa.Column("id", sa.String(length=80), primary_key=True), sa.Column("asset_id", sa.String(length=80), sa.ForeignKey("assets.id"), nullable=False), sa.Column("quantity", sa.Numeric(20, 6), nullable=False), sa.Column("purchase_price", sa.Numeric(20, 6), nullable=False))
    op.create_index("ix_purchase_lots_asset_id", "purchase_lots", ["asset_id"])
    op.create_table("articles", sa.Column("id", sa.String(length=80), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("demo_users.id"), nullable=False), sa.Column("headline", sa.String(length=500), nullable=False), sa.Column("source", sa.String(length=255), nullable=False), sa.Column("published_at", sa.DateTime(timezone=True), nullable=False), sa.Column("relevance", sa.String(length=32), nullable=False), sa.Column("assets", sa.JSON(), nullable=False), sa.Column("industries", sa.JSON(), nullable=False), sa.Column("snippet", sa.Text(), nullable=False), sa.Column("url", sa.String(length=2048), nullable=False), sa.UniqueConstraint("user_id", "url", name="uq_articles_user_url"))
    op.create_index("ix_articles_user_id", "articles", ["user_id"])
    op.create_table("context_summaries", sa.Column("id", sa.String(length=80), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("demo_users.id"), nullable=False), sa.Column("asset_id", sa.String(length=80), sa.ForeignKey("assets.id"), nullable=False), sa.Column("summary", sa.Text(), nullable=False), sa.Column("article_ids", sa.JSON(), nullable=False))
    op.create_index("ix_context_summaries_user_id", "context_summaries", ["user_id"])
    op.create_table("refresh_states", sa.Column("user_id", sa.Integer(), sa.ForeignKey("demo_users.id"), primary_key=True), sa.Column("last_refreshed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(sa.text("INSERT INTO demo_users (id, identifier) VALUES (1, 'demo-user')"))


def downgrade() -> None:
    op.drop_table("refresh_states")
    op.drop_index("ix_context_summaries_user_id", table_name="context_summaries")
    op.drop_table("context_summaries")
    op.drop_index("ix_articles_user_id", table_name="articles")
    op.drop_table("articles")
    op.drop_index("ix_purchase_lots_asset_id", table_name="purchase_lots")
    op.drop_table("purchase_lots")
    op.drop_index("ix_assets_user_id", table_name="assets")
    op.drop_table("assets")
    op.drop_table("demo_users")
