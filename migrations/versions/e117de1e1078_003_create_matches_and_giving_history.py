"""003 create matches and giving history

Revision ID: e117de1e1078
Revises: 5b1810302d36
Create Date: 2026-06-26 09:55:02.696322
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e117de1e1078"
down_revision: Union[str, None] = "5b1810302d36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        "matches",
        sa.Column("match_id", sa.UUID(), primary_key=True),
        sa.Column("donor_id", sa.UUID(), sa.ForeignKey("donors.donor_id"), nullable=False),
        sa.Column("need_id", sa.UUID(), sa.ForeignKey("community_needs.need_id"), nullable=False),
        sa.Column("match_date", sa.TIMESTAMP(), nullable=False),
        sa.Column("match_type", sa.String(50)),
        sa.Column("match_score", sa.Numeric(5, 2)),
        sa.Column("status", sa.String(50)),
        sa.Column("coordinator_notes", sa.Text()),
        sa.Column("confirmed_at", sa.TIMESTAMP()),
    )

    op.create_table(
        "giving_history",
        sa.Column("gift_id", sa.UUID(), primary_key=True),
        sa.Column("donor_id", sa.UUID(), sa.ForeignKey("donors.donor_id"), nullable=False),
        sa.Column("need_id", sa.UUID(), sa.ForeignKey("community_needs.need_id"), nullable=False),
        sa.Column("match_id", sa.UUID(), sa.ForeignKey("matches.match_id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("in_kind_desc", sa.String(255)),
        sa.Column("channel", sa.String(50)),
        sa.Column("transaction_ref", sa.String(100)),
        sa.Column("impact_note", sa.Text()),
        sa.Column("gift_date", sa.TIMESTAMP()),
        sa.Column("created_at", sa.TIMESTAMP()),
    )


def downgrade() -> None:

    op.drop_table("giving_history")
    op.drop_table("matches")