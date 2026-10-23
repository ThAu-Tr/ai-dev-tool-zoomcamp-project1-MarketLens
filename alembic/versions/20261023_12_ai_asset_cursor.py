"""Rotate bounded AI context batches across followed assets."""
from alembic import op
import sqlalchemy as sa


revision = "20261023_12"
down_revision = "20261023_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.add_column(sa.Column("ai_asset_cursor", sa.String(length=80), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.drop_column("ai_asset_cursor")
