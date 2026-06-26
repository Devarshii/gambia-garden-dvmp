"""002 create core tables

Revision ID: 5b1810302d36
Revises: dac150c9cc23
Create Date: 2026-06-26 09:51:03.218899
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5b1810302d36"
down_revision: Union[str, None] = "dac150c9cc23"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "donors",
        sa.Column("donor_id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(150), nullable=False, unique=True),
        sa.Column("location", sa.String(150)),
        sa.Column("interests", sa.ARRAY(sa.Text())),
        sa.Column("giving_capacity", sa.Numeric(12, 2)),
        sa.Column("preferred_causes", sa.ARRAY(sa.Text())),
        sa.Column("preferred_regions", sa.ARRAY(sa.Text())),
        sa.Column("created_at", sa.TIMESTAMP()),
        sa.Column("updated_at", sa.TIMESTAMP()),
    )

    op.create_table(
        "community_needs",
        sa.Column("need_id", sa.UUID(), primary_key=True),
        sa.Column("region_id", sa.UUID(), sa.ForeignKey("regions.region_id"), nullable=False),
        sa.Column("category_id", sa.UUID(), sa.ForeignKey("categories.category_id"), nullable=False),
        sa.Column("coord_id", sa.UUID(), sa.ForeignKey("coordinators.coord_id"), nullable=False),
        sa.Column("village", sa.String(150), nullable=False),
        sa.Column("urgency", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("photo_urls", sa.ARRAY(sa.Text())),
        sa.Column("estimated_cost", sa.Numeric(12, 2)),
        sa.Column("created_at", sa.TIMESTAMP()),
        sa.Column("resolved_at", sa.TIMESTAMP()),
    )


def downgrade() -> None:
    op.drop_table("community_needs")
    op.drop_table("donors")