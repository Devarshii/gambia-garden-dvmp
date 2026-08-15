"""deduplicate and constrain donor need matches

Revision ID: 14203c4f19f5
Revises: e52eaf5b40e8
Create Date: 2026-08-15

This migration removes duplicate donor-to-need match records before
adding a database-level unique constraint.

When duplicates exist, records are preserved in this priority order:

1. confirmed
2. rejected
3. closed
4. proposed or pending
5. not_qualified
6. any other status

Within the same status priority, the newest match is preserved.
Any giving-history references are moved to the preserved record
before duplicate records are deleted.
"""

from typing import Sequence, Union

from alembic import op


# Revision identifiers used by Alembic.
revision: str = "14203c4f19f5"
down_revision: Union[str, None] = "e52eaf5b40e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Deduplicate matches and prevent future donor-need duplicates.
    """
    # Reassign giving-history references from duplicate matches
    # to the match record that will be preserved.
    op.execute(
        """
        WITH ranked_matches AS (
            SELECT
                match_id,
                FIRST_VALUE(match_id) OVER (
                    PARTITION BY donor_id, need_id
                    ORDER BY
                        CASE status
                            WHEN 'confirmed' THEN 1
                            WHEN 'rejected' THEN 2
                            WHEN 'closed' THEN 3
                            WHEN 'proposed' THEN 4
                            WHEN 'pending' THEN 4
                            WHEN 'not_qualified' THEN 5
                            ELSE 6
                        END,
                        match_date DESC NULLS LAST,
                        match_id
                ) AS keeper_match_id,
                ROW_NUMBER() OVER (
                    PARTITION BY donor_id, need_id
                    ORDER BY
                        CASE status
                            WHEN 'confirmed' THEN 1
                            WHEN 'rejected' THEN 2
                            WHEN 'closed' THEN 3
                            WHEN 'proposed' THEN 4
                            WHEN 'pending' THEN 4
                            WHEN 'not_qualified' THEN 5
                            ELSE 6
                        END,
                        match_date DESC NULLS LAST,
                        match_id
                ) AS row_number
            FROM matches
        )
        UPDATE giving_history AS gh
        SET match_id = ranked_matches.keeper_match_id
        FROM ranked_matches
        WHERE gh.match_id = ranked_matches.match_id
          AND ranked_matches.row_number > 1
        """
    )

    # Delete lower-priority duplicate match records.
    op.execute(
        """
        WITH ranked_matches AS (
            SELECT
                match_id,
                ROW_NUMBER() OVER (
                    PARTITION BY donor_id, need_id
                    ORDER BY
                        CASE status
                            WHEN 'confirmed' THEN 1
                            WHEN 'rejected' THEN 2
                            WHEN 'closed' THEN 3
                            WHEN 'proposed' THEN 4
                            WHEN 'pending' THEN 4
                            WHEN 'not_qualified' THEN 5
                            ELSE 6
                        END,
                        match_date DESC NULLS LAST,
                        match_id
                ) AS row_number
            FROM matches
        )
        DELETE FROM matches
        USING ranked_matches
        WHERE matches.match_id = ranked_matches.match_id
          AND ranked_matches.row_number > 1
        """
    )

    op.create_unique_constraint(
        "uq_matches_donor_need",
        "matches",
        [
            "donor_id",
            "need_id",
        ],
    )


def downgrade() -> None:
    """
    Remove the unique constraint.

    Deleted duplicate records are intentionally not recreated.
    """
    op.drop_constraint(
        "uq_matches_donor_need",
        "matches",
        type_="unique",
    )