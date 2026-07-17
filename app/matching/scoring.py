from typing import Any


def normalize_text(value: Any) -> str:
    """
    Convert a value into clean lowercase text.
    """
    if value is None:
        return ""

    return str(value).strip().lower()


def normalize_list(values: Any) -> list[str]:
    """
    Convert arrays, lists, tuples, or comma-separated strings
    into a clean lowercase list.
    """
    if values is None:
        return []

    if isinstance(values, (list, tuple)):
        return [
            normalize_text(value)
            for value in values
            if normalize_text(value)
        ]

    if isinstance(values, str):
        cleaned_value = values.strip()

        if not cleaned_value:
            return []

        cleaned_value = cleaned_value.strip("{}[]")

        return [
            normalize_text(value)
            for value in cleaned_value.split(",")
            if normalize_text(value)
        ]

    return [normalize_text(values)]


def calculate_cause_score(
    preferred_causes: Any,
    category_name: Any,
) -> float:
    """
    Maximum: 35 points.

    Full points are given when:
    - the category exactly matches a preferred cause, or
    - the donor selected all categories.
    """
    causes = normalize_list(preferred_causes)
    category = normalize_text(category_name)

    all_category_values = {
        "all categories",
        "all causes",
        "any category",
        "any cause",
    }

    if any(value in causes for value in all_category_values):
        return 35.0

    if category and category in causes:
        return 35.0

    return 0.0


def calculate_region_score(
    preferred_regions: Any,
    region_name: Any,
) -> float:
    """
    Maximum: 25 points.

    Full points are given when:
    - the region exactly matches a preferred region,
    - the donor selected all regions, or
    - no region preference was provided.
    """
    regions = normalize_list(preferred_regions)
    region = normalize_text(region_name)

    all_region_values = {
        "all regions",
        "all regions of the gambia",
        "any region",
        "the gambia",
    }

    if not regions:
        return 25.0

    if any(value in regions for value in all_region_values):
        return 25.0

    if region and region in regions:
        return 25.0

    return 0.0


def calculate_capacity_score(
    giving_capacity: Any,
    requested_amount: Any,
) -> float:
    """
    Maximum: 20 points.

    The score is based on how much of the estimated cost
    the donor can cover.

    Unknown capacity currently receives 0 points.
    """
    if giving_capacity is None:
        return 0.0

    try:
        capacity = float(giving_capacity)
        amount_needed = float(requested_amount or 0)
    except (TypeError, ValueError):
        return 0.0

    if capacity < 0 or amount_needed <= 0:
        return 0.0

    capacity_ratio = capacity / amount_needed
    score = min(capacity_ratio, 1.0) * 20

    return round(score, 2)


def calculate_priority_score(priority: Any) -> float:
    """
    Maximum: 10 points.

    Supports both database urgency numbers and text values.

    1 = Low
    2 = Medium-Low
    3 = Medium
    4 = High
    5 = Critical
    """
    numeric_priority_scores = {
        1: 2.0,
        2: 4.0,
        3: 5.0,
        4: 8.0,
        5: 10.0,
    }

    try:
        numeric_priority = int(priority)

        if numeric_priority in numeric_priority_scores:
            return numeric_priority_scores[numeric_priority]
    except (TypeError, ValueError):
        pass

    text_priority_scores = {
        "critical": 10.0,
        "urgent": 10.0,
        "high": 8.0,
        "medium": 5.0,
        "medium-low": 4.0,
        "low": 2.0,
    }

    normalized_priority = normalize_text(priority)

    return text_priority_scores.get(normalized_priority, 0.0)


def calculate_history_score(
    same_category_history: bool = False,
    same_region_history: bool = False,
) -> float:
    """
    Maximum: 10 points.

    Same category history: 5 points.
    Same region history: 5 points.
    """
    score = 0.0

    if same_category_history:
        score += 5.0

    if same_region_history:
        score += 5.0

    return score


def calculate_match_score(
    preferred_causes: Any,
    preferred_regions: Any,
    giving_capacity: Any,
    category_name: Any,
    region_name: Any,
    requested_amount: Any,
    priority: Any,
    same_category_history: bool = False,
    same_region_history: bool = False,
) -> dict[str, float]:
    """
    Calculate the complete donor-to-community-need score.

    Maximum score: 100.
    """
    cause_score = calculate_cause_score(
        preferred_causes,
        category_name,
    )

    region_score = calculate_region_score(
        preferred_regions,
        region_name,
    )

    capacity_score = calculate_capacity_score(
        giving_capacity,
        requested_amount,
    )

    priority_score = calculate_priority_score(priority)

    history_score = calculate_history_score(
        same_category_history,
        same_region_history,
    )

    total_score = (
        cause_score
        + region_score
        + capacity_score
        + priority_score
        + history_score
    )

    return {
        "cause_score": cause_score,
        "region_score": region_score,
        "capacity_score": capacity_score,
        "priority_score": priority_score,
        "history_score": history_score,
        "total_score": round(total_score, 2),
    }