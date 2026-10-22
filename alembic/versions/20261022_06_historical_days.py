"""Persist lazily loaded historical market days and exact price snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "20261022_06"
down_revision = "20261021_05"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("historical_days",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("demo_users.id"), primary_key=True),
        sa.Column("market_date", sa.Date(), primary_key=True),
        sa.Column("market_closed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_table("historical_prices",
        sa.Column("id", sa.String(160), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("demo_users.id"), nullable=False),
        sa.Column("market_date", sa.Date(), nullable=False),
        sa.Column("asset_id", sa.String(80), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("exchange", sa.String(120), nullable=False),
        sa.Column("asset_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("price", sa.Numeric(20, 6)),
        sa.Column("currency", sa.String(8)),
        sa.Column("change_percent", sa.Numeric(12, 6)),
        sa.Column("as_of", sa.DateTime(timezone=True)),
        sa.Column("industries", sa.JSON(), nullable=False),
        sa.UniqueConstraint("user_id", "market_date", "asset_id", name="uq_historical_price_day_asset"),
    )
    op.create_index("ix_historical_prices_user_id", "historical_prices", ["user_id"])
    op.create_index("ix_historical_prices_market_date", "historical_prices", ["market_date"])

def downgrade() -> None:
    op.drop_index("ix_historical_prices_market_date", table_name="historical_prices")
    op.drop_index("ix_historical_prices_user_id", table_name="historical_prices")
    op.drop_table("historical_prices")
    op.drop_table("historical_days")
