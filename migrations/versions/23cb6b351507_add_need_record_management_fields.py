"""add need record management fields

Revision ID: 23cb6b351507
Revises: b9ce5b2c56ec
Create Date: 2026-07-26
"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "23cb6b351507"
down_revision: Union[str, None] = "b9ce5b2c56ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    No database changes are required.

    The community_needs table already contains:
    - coordinator_notes
    - resolved_at
    """
    pass


def downgrade() -> None:
    """
    No database changes were made by this migration.
    """
    pass