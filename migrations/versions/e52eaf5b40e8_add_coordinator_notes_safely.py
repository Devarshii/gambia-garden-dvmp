"""add coordinator notes safely

Revision ID: e52eaf5b40e8
Revises: 23cb6b351507
Create Date: 2026-08-14
"""

from typing import Sequence, Union

from alembic import op


# Revision identifiers used by Alembic.
revision: str = "e52eaf5b40e8"
down_revision: Union[str, None] = "23cb6b351507"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add coordinator_notes when it is missing.

    IF NOT EXISTS allows this migration to run safely against the
    current database, where the column may have been added manually.
    """
    op.execute(
        """
        ALTER TABLE community_needs
        ADD COLUMN IF NOT EXISTS coordinator_notes TEXT
        """
    )


def downgrade() -> None:
    """
    Remove coordinator_notes when rolling back this migration.
    """
    op.execute(
        """
        ALTER TABLE community_needs
        DROP COLUMN IF EXISTS coordinator_notes
        """
    )