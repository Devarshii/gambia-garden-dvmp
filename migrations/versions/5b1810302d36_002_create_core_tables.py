"""002 create core tables

Revision ID: 5b1810302d36
Revises: dac150c9cc23
Create Date: 2026-06-26 09:51:03.218899
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "5b1810302d36"
down_revision: Union[str, None] = "dac150c9cc23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "donors",
        sa.Column("donor_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150), nullable=False, unique=True),
        sa.Column("location", sa.String(150), nullable=True),
        sa.Column("interests", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("giving_capacity", sa.Numeric(12, 2), nullable=True),
        sa.Column("preferred_causes", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("preferred_regions", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    op.create_table(
        "community_needs",
        sa.Column("need_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("region_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("regions.region_id"), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("categories.category_id"), nullable=False),
        sa.Column("coord_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coordinators.coord_id"), nullable=False),
        sa.Column("village", sa.String(150), nullable=False),
        sa.Column("urgency", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'open'")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("photo_urls", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("resolved_at", sa.TIMESTAMP(), nullable=True),
        sa.CheckConstraint("urgency BETWEEN 1 AND 5", name="ck_community_needs_urgency_1_5"),
        sa.CheckConstraint(
            "status IN ('open', 'matched', 'fulfilled')",
            name="ck_community_needs_status",
        ),
    )


def downgrade() -> None:
    op.drop_table("community_needs")
    op.drop_table("donors")