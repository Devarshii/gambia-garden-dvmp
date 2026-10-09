
from unittest.mock import MagicMock

from app.matching.database import confirm_match


def make_result(mapping=None, row=None):
    result = MagicMock()
    result.mappings.return_value.first.return_value = mapping
    result.first.return_value = row
    return result


def test_confirm_match_success():
    connection = MagicMock()

    connection.execute.side_effect = [
        make_result({"need_id": "need-1"}),
        make_result({"need_id": "need-1", "status": "open"}),
        make_result(row=None),
        make_result(
            {"match_id": "match-1", "need_id": "need-1"}
        ),
        make_result(),
        make_result(),
    ]

    result = confirm_match(
        connection,
        match_id="match-1",
        coordinator_notes="Approved",
    )

    assert result["match_id"] == "match-1"
    assert connection.execute.call_count == 6

    queries = [
        str(call.args[0])
        for call in connection.execute.call_args_list
    ]

    assert "FOR UPDATE" in queries[1]
    assert "status = 'confirmed'" in queries[3]
    assert "status = 'rejected'" in queries[4]
    assert "status = 'matched'" in queries[5]


def test_confirm_match_blocks_already_matched_need():
    connection = MagicMock()

    connection.execute.side_effect = [
        make_result({"need_id": "need-1"}),
        make_result({"need_id": "need-1", "status": "matched"}),
    ]

    result = confirm_match(connection, "match-2")

    assert result is None
    assert connection.execute.call_count == 2


def test_confirm_match_blocks_existing_confirmation():
    connection = MagicMock()

    connection.execute.side_effect = [
        make_result({"need_id": "need-1"}),
        make_result({"need_id": "need-1", "status": "open"}),
        make_result(row=("match-1",)),
    ]

    result = confirm_match(connection, "match-2")

    assert result is None
    assert connection.execute.call_count == 3


def test_confirm_match_missing_match():
    connection = MagicMock()

    connection.execute.return_value = make_result(mapping=None)

    result = confirm_match(connection, "missing-match")

    assert result is None
    assert connection.execute.call_count == 1


def test_confirm_match_non_proposed_match():
    connection = MagicMock()

    connection.execute.side_effect = [
        make_result({"need_id": "need-1"}),
        make_result({"need_id": "need-1", "status": "open"}),
        make_result(row=None),
        make_result(mapping=None),
    ]

    result = confirm_match(connection, "match-1")

    assert result is None
    assert connection.execute.call_count == 4
