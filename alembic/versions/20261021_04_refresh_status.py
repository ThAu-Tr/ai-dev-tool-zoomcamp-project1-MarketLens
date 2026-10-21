"""Persist refresh availability and unsupported symbols."""
from alembic import op
import sqlalchemy as sa

revision = "20261021_04"
down_revision = "20261021_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.add_column(sa.Column("status", sa.String(length=16), nullable=False, server_default="never"))
        batch_op.add_column(sa.Column("unavailable_tickers", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.drop_column("unavailable_tickers")
        batch_op.drop_column("status")
