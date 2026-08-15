import os
from typing import Callable, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.matching.database import (
    insert_match,
    match_exists,
    update_match,
)
from app.matching.scoring import calculate_match_score


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

engine = create_engine(DATABASE_URL)


ProgressCallback = Optional[Callable[[str, str, float], None]]


def get_donors(connection):
    """
    Read all donors from the database.
    """
    result = connection.execute(
        text(
            """
            SELECT
                donor_id,
                name,
                preferred_causes,
                preferred_regions,
                giving_capacity
            FROM donors
            """
        )
    )

    return result.mappings().all()


def get_community_needs(connection):
    """
    Read all open community needs with their category and region.
    """
    result = connection.execute(
        text(
            """
            SELECT
                cn.need_id,
                cn.description AS need_name,
                cn.estimated_cost AS requested_amount,
                cn.urgency AS priority,
                cn.category_id,
                cn.region_id,
                c.category_code AS category_name,
                r.region_name
            FROM community_needs cn
            JOIN categories c
                ON cn.category_id = c.category_id
            JOIN regions r
                ON cn.region_id = r.region_id
            WHERE LOWER(cn.status) = 'open'
            """
        )
    )

    return result.mappings().all()


def get_giving_history(connection):
    """
    Read donor history with the category and region of each
    community need that previously received a gift.

    Records without a linked need cannot be used for category-
    or region-based history scoring.
    """
    result = connection.execute(
        text(
            """
            SELECT DISTINCT
                gh.donor_id,
                cn.category_id,
                cn.region_id
            FROM giving_history gh
            JOIN community_needs cn
                ON gh.need_id = cn.need_id
            WHERE gh.need_id IS NOT NULL
            """
        )
    )

    return result.mappings().all()


def generate_matches(progress_callback: ProgressCallback = None):
    """
    Generate automatic donor-to-community-need matches.

    Qualified matches are inserted when new and updated when the
    donor-to-need combination already exists.

    Giving history contributes:
    - 5 points for previous giving in the same category
    - 5 points for previous giving in the same region

    Parameters
    ----------
    progress_callback:
        Optional function used by Streamlit or another interface.

        The callback receives:
        - stage name
        - progress message
        - progress value between 0.0 and 1.0

    Returns
    -------
    dict
        Structured summary of the matching run.
    """

    def report_progress(stage, message, progress):
        """
        Send progress information when a callback is provided.
        """
        if progress_callback:
            progress_callback(stage, message, progress)

    donors = []
    needs = []
    giving_history = []

    qualified_matches = 0
    inserted_matches = 0
    updated_matches = 0
    skipped_matches = 0
    errors = 0

    report_progress(
        "loading_donors",
        "Loading donors from the database...",
        0.10,
    )

    with engine.connect() as connection:
        donors = get_donors(connection)

        report_progress(
            "loading_needs",
            "Loading open community needs...",
            0.20,
        )

        needs = get_community_needs(connection)

        report_progress(
            "loading_history",
            "Loading donor giving history...",
            0.25,
        )

        giving_history = get_giving_history(connection)

    category_history = {
        (history["donor_id"], history["category_id"])
        for history in giving_history
    }

    region_history = {
        (history["donor_id"], history["region_id"])
        for history in giving_history
    }

    total_combinations = len(donors) * len(needs)

    report_progress(
        "evaluating_matches",
        "Evaluating donor and community-need combinations...",
        0.30,
    )

    try:
        # engine.begin() creates one database transaction.
        # If an exception occurs, SQLAlchemy automatically rolls it back.
        with engine.begin() as connection:
            combinations_processed = 0

            for donor in donors:
                for need in needs:
                    combinations_processed += 1

                    try:
                        same_category_history = (
                            donor["donor_id"],
                            need["category_id"],
                        ) in category_history

                        same_region_history = (
                            donor["donor_id"],
                            need["region_id"],
                        ) in region_history

                        score_breakdown = calculate_match_score(
                            preferred_causes=donor["preferred_causes"],
                            preferred_regions=donor["preferred_regions"],
                            giving_capacity=donor["giving_capacity"],
                            category_name=need["category_name"],
                            region_name=need["region_name"],
                            requested_amount=need["requested_amount"],
                            priority=need["priority"],
                            same_category_history=same_category_history,
                            same_region_history=same_region_history,
                        )

                        total_score = score_breakdown["total_score"]

                        if total_score < 50:
                            skipped_matches += 1
                        else:
                            qualified_matches += 1

                            existing_match = match_exists(
                                connection=connection,
                                donor_id=donor["donor_id"],
                                need_id=need["need_id"],
                            )

                            if existing_match:
                                update_match(
                                    connection=connection,
                                    donor_id=donor["donor_id"],
                                    need_id=need["need_id"],
                                    match_score=total_score,
                                    score_breakdown=score_breakdown,
                                )

                                updated_matches += 1

                            else:
                                insert_match(
                                    connection=connection,
                                    donor_id=donor["donor_id"],
                                    need_id=need["need_id"],
                                    match_score=total_score,
                                    score_breakdown=score_breakdown,
                                )

                                inserted_matches += 1

                    except Exception:
                        errors += 1
                        raise

                    if total_combinations > 0:
                        evaluation_progress = (
                            combinations_processed / total_combinations
                        )

                        overall_progress = 0.30 + (
                            evaluation_progress * 0.60
                        )

                        report_progress(
                            "evaluating_matches",
                            (
                                f"Evaluated {combinations_processed} of "
                                f"{total_combinations} combinations..."
                            ),
                            min(overall_progress, 0.90),
                        )

        report_progress(
            "completed",
            "Matching engine completed successfully.",
            1.0,
        )

    except Exception as error:
        report_progress(
            "failed",
            f"Matching engine failed: {error}",
            1.0,
        )

        raise

    summary = {
        "donors_scanned": len(donors),
        "open_needs_scanned": len(needs),
        "giving_history_records": len(giving_history),
        "total_combinations": total_combinations,
        "qualified_matches": qualified_matches,
        "inserted_matches": inserted_matches,
        "updated_matches": updated_matches,
        "skipped_matches": skipped_matches,
        "errors": errors,
    }

    print("\n--------------------------------------")
    print(f"Donors scanned: {summary['donors_scanned']}")
    print(f"Open needs scanned: {summary['open_needs_scanned']}")
    print(
        "Giving-history records loaded: "
        f"{summary['giving_history_records']}"
    )
    print(f"Combinations evaluated: {summary['total_combinations']}")
    print(f"Qualified matches: {summary['qualified_matches']}")
    print(f"Inserted: {summary['inserted_matches']}")
    print(f"Updated: {summary['updated_matches']}")
    print(f"Skipped below score 50: {summary['skipped_matches']}")
    print(f"Errors: {summary['errors']}")
    print("--------------------------------------\n")

    return summary


if __name__ == "__main__":
    generate_matches()