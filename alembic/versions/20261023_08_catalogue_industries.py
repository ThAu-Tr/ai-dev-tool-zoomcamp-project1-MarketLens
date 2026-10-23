"""Expand the supported industries for the bounded asset catalogue.

Revision ID: 20261023_08
Revises: 20261022_09
Create Date: 2026-10-23
"""

from alembic import op
import sqlalchemy as sa


revision = "20261023_08"
down_revision = "20261022_09"
branch_labels = None
depends_on = None


def upgrade() -> None:
    industries = sa.table("industries", sa.column("id", sa.String), sa.column("name", sa.String))
    op.bulk_insert(industries, [
        {"id": "automotive", "name": "Automotive"},
        {"id": "technology-hardware", "name": "Technology hardware"},
        {"id": "communication-services", "name": "Communication services"},
        {"id": "consumer-discretionary", "name": "Consumer discretionary"},
        {"id": "financial-services", "name": "Financial services"},
        {"id": "healthcare", "name": "Healthcare"},
        {"id": "traditional-energy", "name": "Energy"},
        {"id": "consumer-staples", "name": "Consumer staples"},
        {"id": "technology", "name": "Technology"},
        {"id": "international-equities", "name": "International equities"},
        {"id": "emerging-markets", "name": "Emerging markets"},
        {"id": "commodities", "name": "Commodities"},
        {"id": "us-equities", "name": "US equities"},
    ])


def downgrade() -> None:
    # Keep rows so existing user follows remain valid on downgrade.
    pass
