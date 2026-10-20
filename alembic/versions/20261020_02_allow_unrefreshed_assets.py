"""Allow assets awaiting their first quote and prevent duplicate watchlist entries.

Revision ID: 20261020_02
Revises: 20261020_01
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20261020_02"
down_revision = "20261020_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("assets") as batch_op:
        batch_op.alter_column("price", existing_type=sa.Numeric(20, 6), nullable=True)
        batch_op.alter_column("currency", existing_type=sa.String(length=8), nullable=True)
        batch_op.alter_column("change_percent", existing_type=sa.Numeric(12, 6), nullable=True)
        batch_op.alter_column("as_of", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch_op.create_unique_constraint("uq_assets_user_ticker_exchange", ["user_id", "ticker", "exchange"])


def downgrade() -> None:
    with op.batch_alter_table("assets") as batch_op:
        batch_op.drop_constraint("uq_assets_user_ticker_exchange", type_="unique")
        batch_op.alter_column("as_of", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch_op.alter_column("change_percent", existing_type=sa.Numeric(12, 6), nullable=False)
        batch_op.alter_column("currency", existing_type=sa.String(length=8), nullable=False)
        batch_op.alter_column("price", existing_type=sa.Numeric(20, 6), nullable=False)
