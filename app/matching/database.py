import uuid

from sqlalchemy import text


def match_exists(connection, donor_id, need_id):
    """
    Check whether a donor-to-community-need match already exists.
    """
    result = connection.execute(
        text(
            """
            SELECT match_id
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

    return result.fetchone()


def insert_match(
    connection,
    donor_id,
    need_id,
    match_score,
):
    """
    Insert a new automatically generated match.
    """
    connection.execute(
        text(
            """
            INSERT INTO matches (
                match_id,
                donor_id,
                need_id,
                match_type,
                match_score
            )
            VALUES (
                :match_id,
                :donor_id,
                :need_id,
                :match_type,
                :match_score
            )
            """
        ),
        {
            "match_id": str(uuid.uuid4()),
            "donor_id": donor_id,
            "need_id": need_id,
            "match_type": "auto",
            "match_score": match_score,
        },
    )


def update_match(
    connection,
    donor_id,
    need_id,
    match_score,
):
    """
    Update the score and date of an existing match.
    """
    connection.execute(
        text(
            """
            UPDATE matches
            SET
                match_score = :match_score,
                match_date = CURRENT_TIMESTAMP
            WHERE donor_id = :donor_id
              AND need_id = :need_id
            """
        ),
        {
            "match_score": match_score,
            "donor_id": donor_id,
            "need_id": need_id,
        },
    )