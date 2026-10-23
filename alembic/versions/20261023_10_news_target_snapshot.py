"""Track the targets covered by the incremental news checkpoint."""
from alembic import op
import sqlalchemy as sa

revision = "20261023_10"
down_revision = "20261022_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.add_column(sa.Column("news_asset_tickers", sa.JSON(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("news_industry_ids", sa.JSON(), nullable=False, server_default="[]"))


def downgrade() -> None:
    with op.batch_alter_table("refresh_states") as batch_op:
        batch_op.drop_column("news_industry_ids")
        batch_op.drop_column("news_asset_tickers")
