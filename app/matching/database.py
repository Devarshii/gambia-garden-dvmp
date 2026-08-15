import json
import uuid

from sqlalchemy import text


# ---------------------------------------------------------
# Match generation functions
# ---------------------------------------------------------

def match_exists(connection, donor_id, need_id):
    """
    Check whether a donor-to-community-need match already exists.
    """
    result = connection.execute(
        text(
            """
            SELECT
                match_id,
                status
            FROM matches
            WHERE donor_id = :donor_id
              AND need_id = :need_id
            """
        ),
        {
            "donor_id": donor_id,
            "need_id": need_id,
        },
    )

    return result.mappings().first()


def insert_match(
    connection,
    donor_id,
    need_id,
    match_score,
    score_breakdown=None,
):
    """
    Insert a new automatically generated proposed match.

    If another process creates the same donor-to-need match
    concurrently, update its score safely instead of creating
    a duplicate or failing the transaction.

    Confirmed and rejected statuses are preserved.
    """
    result = connection.execute(
        text(
            """
            INSERT INTO matches (
                match_id,
                donor_id,
                need_id,
                match_type,
                match_score,
                score_breakdown,
                status
            )
            VALUES (
                :match_id,
                :donor_id,
                :need_id,
                :match_type,
                :match_score,
                CAST(:score_breakdown AS JSONB),
                :status
            )
            ON CONFLICT (
                donor_id,
                need_id
            )
            DO UPDATE
            SET
                match_score = EXCLUDED.match_score,
                score_breakdown = EXCLUDED.score_breakdown,
                match_date = CURRENT_TIMESTAMP,
                status = CASE
                    WHEN matches.status IS NULL
                        THEN 'proposed'
                    WHEN matches.status = 'not_qualified'
                        THEN 'proposed'
                    ELSE matches.status
                END
            RETURNING match_id
            """
        ),
        {
            "match_id": str(uuid.uuid4()),
            "donor_id": donor_id,
            "need_id": need_id,
            "match_type": "auto",
            "match_score": match_score,
            "score_breakdown": json.dumps(
                score_breakdown or {}
            ),
            "status": "proposed",
        },
    )

    return result.fetchone()


def update_match(
    connection,
    donor_id,
    need_id,
    match_score,
    score_breakdown=None,
):
    """
    Update an existing match's score, score breakdown,
    and match date.

    A confirmed or rejected status is not overwritten.
    """
    connection.execute(
        text(
            """
            UPDATE matches
            SET
                match_score = :match_score,
                score_breakdown = CAST(
                    :score_breakdown AS JSONB
                ),
                match_date = CURRENT_TIMESTAMP,
                status = CASE
                    WHEN status IS NULL THEN 'proposed'
                    WHEN status = 'not_qualified' THEN 'proposed'
                    ELSE status
                END
            WHERE donor_id = :donor_id
              AND need_id = :need_id
            """
        ),
        {
            "match_score": match_score,
            "score_breakdown": json.dumps(
                score_breakdown or {}
            ),
            "donor_id": donor_id,
            "need_id": need_id,
        },
    )


def mark_match_not_qualified(
    connection,
    donor_id,
    need_id,
    match_score,
    score_breakdown=None,
):
    """
    Close an existing automated proposal when its recalculated
    score falls below the matching threshold.

    Confirmed and manually rejected decisions are not overwritten.
    """
    result = connection.execute(
        text(
            """
            UPDATE matches
            SET
                match_score = :match_score,
                score_breakdown = CAST(
                    :score_breakdown AS JSONB
                ),
                match_date = CURRENT_TIMESTAMP,
                status = 'not_qualified',
                confirmed_at = NULL
            WHERE donor_id = :donor_id
              AND need_id = :need_id
              AND (
                  status IS NULL
                  OR status IN (
                      'pending',
                      'proposed',
                      'not_qualified'
                  )
              )
            RETURNING match_id
            """
        ),
        {
            "match_score": match_score,
            "score_breakdown": json.dumps(
                score_breakdown or {}
            ),
            "donor_id": donor_id,
            "need_id": need_id,
        },
    )

    return result.fetchone()


# ---------------------------------------------------------
# Community needs functions
# ---------------------------------------------------------

def get_community_needs(connection):
    """
    Retrieve community needs along with region and category
    information for the coordinator dashboard.
    """
    result = connection.execute(
        text(
            """
            SELECT
                cn.need_id,
                cn.village,
                r.region_name AS region,
                c.label AS category,
                cn.urgency,
                cn.status,
                cn.estimated_cost,
                cn.created_at AS date_submitted,
                cn.description,
                cn.coordinator_notes,
                cn.resolved_at
            FROM community_needs cn
            JOIN regions r
                ON cn.region_id = r.region_id
            JOIN categories c
                ON cn.category_id = c.category_id
            WHERE cn.status IN (
                'open',
                'matched',
                'fulfilled'
            )
            ORDER BY cn.created_at DESC
            """
        )
    )

    return result.mappings().all()


# ---------------------------------------------------------
# Match review functions
# ---------------------------------------------------------

def get_proposed_matches(connection):
    """
    Retrieve matches that are waiting for coordinator review.

    Only matches with a pending or proposed status are returned.
    """
    result = connection.execute(
        text(
            """
            SELECT
                m.match_id,
                m.match_date,
                m.match_type,
                m.match_score,
                m.score_breakdown,
                m.status AS match_status,
                m.coordinator_notes,

                d.donor_id,
                d.name AS donor_name,

                cn.need_id,
                cn.village,
                cn.description,
                cn.urgency,
                cn.estimated_cost,
                cn.status AS need_status,

                r.region_name AS region,
                c.label AS category

            FROM matches m

            JOIN donors d
                ON m.donor_id = d.donor_id

            JOIN community_needs cn
                ON m.need_id = cn.need_id

            JOIN regions r
                ON cn.region_id = r.region_id

            JOIN categories c
                ON cn.category_id = c.category_id

            WHERE m.status IN (
                'pending',
                'proposed'
            )

            ORDER BY
                m.match_score DESC NULLS LAST,
                m.match_date DESC
            """
        )
    )

    return result.mappings().all()


def confirm_match(
    connection,
    match_id,
    coordinator_notes=None,
):
    """
    Confirm a proposed match and update the related community need
    to matched in the same database transaction.
    """
    result = connection.execute(
        text(
            """
            UPDATE matches
            SET
                status = 'confirmed',
                coordinator_notes = :coordinator_notes,
                confirmed_at = CURRENT_TIMESTAMP
            WHERE match_id = :match_id
              AND status IN (
                  'pending',
                  'proposed'
              )
            RETURNING
                match_id,
                need_id
            """
        ),
        {
            "match_id": match_id,
            "coordinator_notes": coordinator_notes,
        },
    )

    confirmed_match = result.mappings().first()

    if not confirmed_match:
        return None

    connection.execute(
        text(
            """
            UPDATE community_needs
            SET
                status = 'matched',
                resolved_at = NULL
            WHERE need_id = :need_id
              AND status IN (
                  'open',
                  'matched'
              )
            """
        ),
        {
            "need_id": confirmed_match["need_id"],
        },
    )

    return confirmed_match


def reject_match(
    connection,
    match_id,
    coordinator_notes=None,
):
    """
    Reject a proposed match.

    Updates the status and coordinator notes.
    """
    result = connection.execute(
        text(
            """
            UPDATE matches
            SET
                status = 'rejected',
                coordinator_notes = :coordinator_notes,
                confirmed_at = NULL
            WHERE match_id = :match_id
              AND status IN (
                  'pending',
                  'proposed'
              )
            RETURNING match_id
            """
        ),
        {
            "match_id": match_id,
            "coordinator_notes": coordinator_notes,
        },
    )

    return result.fetchone()