"""make need_id and match_id nullable

Revision ID: 5791605a4e62
Revises: e117de1e1078
Create Date: 2026-07-09
"""

from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "5791605a4e62"
down_revision = "e117de1e1078"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "giving_history",
        "need_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    op.alter_column(
        "giving_history",
        "match_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "giving_history",
        "match_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    op.alter_column(
        "giving_history",
        "need_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )