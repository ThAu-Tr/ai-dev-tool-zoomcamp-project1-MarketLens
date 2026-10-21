"""Allow optional provider snippets and record direct-news freshness."""

from alembic import op
import sqlalchemy as sa


revision = "20261021_05"
down_revision = "20261021_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("articles") as batch_op:
        batch_op.alter_column("snippet", existing_type=sa.Text(), nullable=True)
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.add_column(sa.Column("news_status", sa.String(length=16), nullable=False, server_default="current"))


def downgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.drop_column("news_status")
    with op.batch_alter_table("articles") as batch_op:
        batch_op.alter_column("snippet", existing_type=sa.Text(), nullable=False)
