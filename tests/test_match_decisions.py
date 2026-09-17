from unittest.mock import MagicMock

from app.matching.database import (
    insert_match,
    update_match,
    mark_match_not_qualified,
)


def make_connection_with_no_updated_row():
    """
    Create a fake database connection that simulates a protected
    confirmed/rejected match where the UPDATE affects no row.
    """
    connection = MagicMock()

    result = MagicMock()
    result.fetchone.return_value = None

    connection.execute.return_value = result

    return connection


def test_insert_match_protects_final_decisions():
    """
    Verify that insert_match's conflict query only allows
    recalculation of non-final match statuses.
    """
    connection = make_connection_with_no_updated_row()

    insert_match(
        connection=connection,
        donor_id="donor-1",
        need_id="need-1",
        match_score=90.0,
        score_breakdown={"cause_score": 35.0},
    )

    sql = str(connection.execute.call_args.args[0])

    assert "ON CONFLICT" in sql
    assert "'pending'" in sql
    assert "'proposed'" in sql
    assert "'not_qualified'" in sql

    # Final coordinator decisions must not be included
    # in the statuses eligible for recalculation.
    assert "'confirmed'" not in sql
    assert "'rejected'" not in sql


def test_update_match_protects_final_decisions():
    """
    Verify that update_match only changes matches that have
    not received a final coordinator decision.
    """
    connection = make_connection_with_no_updated_row()

    result = update_match(
        connection=connection,
        donor_id="donor-1",
        need_id="need-1",
        match_score=75.0,
        score_breakdown={"region_score": 25.0},
    )

    sql = str(connection.execute.call_args.args[0])

    assert "'pending'" in sql
    assert "'proposed'" in sql
    assert "'not_qualified'" in sql

    assert "'confirmed'" not in sql
    assert "'rejected'" not in sql

    assert result is None


def test_mark_not_qualified_protects_final_decisions():
    """
    Verify that confirmed and rejected matches cannot later
    be changed to not_qualified by the matching engine.
    """
    connection = make_connection_with_no_updated_row()

    result = mark_match_not_qualified(
        connection=connection,
        donor_id="donor-1",
        need_id="need-1",
        match_score=40.0,
        score_breakdown={"total_score": 40.0},
    )

    sql = str(connection.execute.call_args.args[0])

    assert "'pending'" in sql
    assert "'proposed'" in sql
    assert "'not_qualified'" in sql

    assert "'confirmed'" not in sql
    assert "'rejected'" not in sql

    assert result is None