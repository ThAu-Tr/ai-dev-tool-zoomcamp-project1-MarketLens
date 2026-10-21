"""Persist the supported industry catalogue and demo-user follows.

Revision ID: 20261021_03
Revises: 20261020_02
Create Date: 2026-10-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20261021_03"
down_revision = "20261020_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("industries", sa.Column("id", sa.String(length=80), primary_key=True), sa.Column("name", sa.String(length=255), nullable=False, unique=True))
    op.create_table("industry_follows", sa.Column("user_id", sa.Integer(), sa.ForeignKey("demo_users.id"), primary_key=True), sa.Column("industry_id", sa.String(length=80), sa.ForeignKey("industries.id"), primary_key=True))
    op.bulk_insert(sa.table("industries", sa.column("id", sa.String), sa.column("name", sa.String)), [
        {"id": "ai", "name": "AI"}, {"id": "banking", "name": "Banking"},
        {"id": "energy", "name": "Renewable energy"}, {"id": "semi", "name": "Semiconductors"},
        {"id": "software", "name": "Enterprise software"},
    ])


def downgrade() -> None:
    op.drop_table("industry_follows")
    op.drop_table("industries")
