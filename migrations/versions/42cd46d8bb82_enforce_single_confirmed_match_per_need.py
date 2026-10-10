
"""Enforce a single confirmed match per community need.

Revision ID: 42cd46d8bb82
Revises: 6185a5977580
"""

from typing import Sequence, Union

from alembic import op


# Revision identifiers
revision: str = "42cd46d8bb82"
down_revision: Union[str, None] = "6185a5977580"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_matches_one_confirmed_per_need
        ON matches (need_id)
        WHERE status = 'confirmed'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP INDEX IF EXISTS uq_matches_one_confirmed_per_need
        """
    )
