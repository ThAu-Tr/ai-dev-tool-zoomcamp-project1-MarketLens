"""Persist the bounded AI refresh checkpoint (no existing data changes)."""
from alembic import op
import sqlalchemy as sa

revision = "20261022_09"
down_revision = "20261022_08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.add_column(sa.Column("ai_checked_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.drop_column("ai_checked_at")
