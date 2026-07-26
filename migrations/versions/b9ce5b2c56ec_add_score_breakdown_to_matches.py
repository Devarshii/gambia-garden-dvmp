"""add score breakdown to matches

Revision ID: b9ce5b2c56ec
Revises: 5791605a4e62
Create Date: 2026-07-24 11:53:19.225016
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers, used by Alembic.
revision: str = "b9ce5b2c56ec"
down_revision: Union[str, None] = "5791605a4e62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column(
            "score_breakdown",
            postgresql.JSONB(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("matches", "score_breakdown")