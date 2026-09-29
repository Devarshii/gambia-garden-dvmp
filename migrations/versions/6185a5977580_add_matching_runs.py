"""add matching runs

Revision ID: 6185a5977580
Revises: 0065f64c62e3
Create Date: 2026-09-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6185a5977580"
down_revision: Union[str, Sequence[str], None] = "0065f64c62e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "matching_runs",
        sa.Column(
            "run_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "donors_scanned",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "open_needs_scanned",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "giving_history_records",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_combinations",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "qualified_matches",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "inserted_matches",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "updated_matches",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "not_qualified_matches",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "skipped_matches",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "errors",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("run_id"),
    )


def downgrade() -> None:
    op.drop_table("matching_runs")