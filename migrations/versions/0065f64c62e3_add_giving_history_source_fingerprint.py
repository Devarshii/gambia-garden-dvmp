"""add giving history source fingerprint

Revision ID: 0065f64c62e3
Revises: 14203c4f19f5
Create Date: 2026-09-17 16:57:00.281704

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0065f64c62e3"
down_revision: Union[str, None] = "14203c4f19f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "giving_history",
        sa.Column(
            "source_fingerprint",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_giving_history_source_fingerprint",
        "giving_history",
        ["source_fingerprint"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_giving_history_source_fingerprint",
        "giving_history",
        type_="unique",
    )

    op.drop_column(
        "giving_history",
        "source_fingerprint",
    )