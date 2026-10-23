"""Persist a safe reason when AI context is not available."""
from alembic import op
import sqlalchemy as sa


revision = "20261023_11"
down_revision = "20261023_10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.add_column(sa.Column("ai_status", sa.String(length=24), nullable=False, server_default="unknown"))


def downgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.drop_column("ai_status")
