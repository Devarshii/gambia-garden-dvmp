"""003 create matches and giving history

Revision ID: e117de1e1078
Revises: 5b1810302d36
Create Date: 2026-06-26 09:55:02.696322
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e117de1e1078"
down_revision: Union[str, None] = "5b1810302d36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        "matches",
        sa.Column("match_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("donor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("donors.donor_id"), nullable=False),
        sa.Column("need_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("community_needs.need_id"), nullable=False),
        sa.Column("match_date", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("match_type", sa.String(50), nullable=False),
        sa.Column("match_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("coordinator_notes", sa.Text(), nullable=True),
        sa.Column("confirmed_at", sa.TIMESTAMP(), nullable=True),
        sa.CheckConstraint(
            "match_type IN ('manual', 'auto')",
            name="ck_matches_match_type",
        ),
    )

    op.create_table(
        "giving_history",
        sa.Column("gift_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("donor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("donors.donor_id"), nullable=False),
        sa.Column("need_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("community_needs.need_id"), nullable=False),
        sa.Column("match_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matches.match_id"), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("in_kind_desc", sa.String(255), nullable=True),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("transaction_ref", sa.String(100), nullable=True),
        sa.Column("impact_note", sa.Text(), nullable=True),
        sa.Column("gift_date", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "channel IN ('Sendwave', 'Wave', 'other')",
            name="ck_giving_history_channel",
        ),
    )

    # Index supports filtering community needs by geography, category, urgency, and workflow status.
    op.create_index(
        "ix_community_needs_region_category_urgency_status",
        "community_needs",
        ["region_id", "category_id", "urgency", "status"],
    )

    # Index supports donor-to-need match lookup and filtering by match status.
    op.create_index(
        "ix_matches_donor_need_status",
        "matches",
        ["donor_id", "need_id", "status"],
    )

    # Index supports donor giving history and need-level donation tracking.
    op.create_index(
        "ix_giving_history_donor_need",
        "giving_history",
        ["donor_id", "need_id"],
    )


def downgrade() -> None:

    op.drop_index("ix_giving_history_donor_need", table_name="giving_history")
    op.drop_index("ix_matches_donor_need_status", table_name="matches")
    op.drop_index("ix_community_needs_region_category_urgency_status", table_name="community_needs")

    op.drop_table("giving_history")
    op.drop_table("matches")