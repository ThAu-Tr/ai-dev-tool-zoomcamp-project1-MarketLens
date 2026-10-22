"""Persist the daily market-context query checkpoint."""

from alembic import op
import sqlalchemy as sa


revision = "20261022_08"
down_revision = "20261022_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.add_column(sa.Column("market_context_checked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.drop_column("market_context_checked_at")
