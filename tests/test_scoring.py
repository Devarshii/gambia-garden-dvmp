from app.matching.scoring import (
    calculate_cause_score,
    calculate_region_score,
    calculate_capacity_score,
    calculate_priority_score,
    calculate_history_score,
    calculate_match_score,
)


def test_exact_cause_match():
    assert calculate_cause_score(["Education"], "Education") == 35.0


def test_broad_cause_preference():
    assert calculate_cause_score(["All Categories"], "Healthcare") == 15.0


def test_no_cause_match():
    assert calculate_cause_score(["Education"], "Healthcare") == 0.0


def test_exact_region_match():
    assert calculate_region_score(["West Coast"], "West Coast") == 25.0


def test_broad_region_preference():
    assert calculate_region_score(["All Regions"], "West Coast") == 10.0


def test_no_region_match():
    assert calculate_region_score(["North Bank"], "West Coast") == 0.0


def test_full_capacity_score():
    assert calculate_capacity_score(1000, 1000) == 20.0


def test_half_capacity_score():
    assert calculate_capacity_score(500, 1000) == 10.0


def test_capacity_score_is_capped():
    assert calculate_capacity_score(2000, 1000) == 20.0


def test_missing_capacity_scores_zero():
    assert calculate_capacity_score(None, 1000) == 0.0


def test_priority_scores():
    assert calculate_priority_score(1) == 2.0
    assert calculate_priority_score(3) == 5.0
    assert calculate_priority_score(5) == 10.0


def test_text_priority_score():
    assert calculate_priority_score("high") == 8.0
    assert calculate_priority_score("critical") == 10.0


def test_history_score():
    assert calculate_history_score(False, False) == 0.0
    assert calculate_history_score(True, False) == 5.0
    assert calculate_history_score(False, True) == 5.0
    assert calculate_history_score(True, True) == 10.0


def test_complete_known_match_score():
    result = calculate_match_score(
        preferred_causes=["Education"],
        preferred_regions=["West Coast"],
        giving_capacity=1000,
        category_name="Education",
        region_name="West Coast",
        requested_amount=1000,
        priority=5,
        same_category_history=True,
        same_region_history=True,
    )

    assert result["cause_score"] == 35.0
    assert result["region_score"] == 25.0
    assert result["capacity_score"] == 20.0
    assert result["priority_score"] == 10.0
    assert result["history_score"] == 10.0
    assert result["total_score"] == 100.0