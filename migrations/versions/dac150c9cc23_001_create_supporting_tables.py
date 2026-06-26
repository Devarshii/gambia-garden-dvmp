"""001 create supporting tables

Revision ID: dac150c9cc23
Revises:
Create Date: 2026-06-26 09:45:26.224282
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "dac150c9cc23"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regions",
        sa.Column("region_id", sa.UUID(), primary_key=True),
        sa.Column("region_code", sa.String(50), nullable=False),
        sa.Column("region_name", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text()),
    )

    op.create_table(
        "categories",
        sa.Column("category_id", sa.UUID(), primary_key=True),
        sa.Column("category_code", sa.String(50), nullable=False, unique=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )

    op.create_table(
        "coordinators",
        sa.Column("coord_id", sa.UUID(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(150), nullable=False, unique=True),
        sa.Column("phone", sa.String(30)),
        sa.Column("region_id", sa.UUID(), sa.ForeignKey("regions.region_id")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.TIMESTAMP()),
    )


def downgrade() -> None:
    op.drop_table("coordinators")
    op.drop_table("categories")
    op.drop_table("regions")