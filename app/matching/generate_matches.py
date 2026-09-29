import os
import uuid
from typing import Callable, Optional

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from app.matching.database import (
    insert_match,
    mark_match_not_qualified,
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

# One PostgreSQL advisory-lock ID is used for the matching engine.
# Only one database session can hold this lock at a time.
MATCHING_ENGINE_LOCK_ID = 84739201


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


def acquire_matching_lock(connection):
    """
    Try to acquire the matching-engine advisory lock.

    Returns False when another database session already has
    a matching run in progress.
    """
    result = connection.execute(
        text(
            """
            SELECT pg_try_advisory_lock(:lock_id)
            """
        ),
        {
            "lock_id": MATCHING_ENGINE_LOCK_ID,
        },
    )

    return bool(result.scalar())


def release_matching_lock(connection):
    """
    Release the matching-engine advisory lock.
    """
    connection.execute(
        text(
            """
            SELECT pg_advisory_unlock(:lock_id)
            """
        ),
        {
            "lock_id": MATCHING_ENGINE_LOCK_ID,
        },
    )


def create_matching_run(connection):
    """
    Create a persistent matching-run record.
    """
    run_id = uuid.uuid4()

    connection.execute(
        text(
            """
            INSERT INTO matching_runs (
                run_id,
                status
            )
            VALUES (
                :run_id,
                'running'
            )
            """
        ),
        {
            "run_id": run_id,
        },
    )

    connection.commit()

    return run_id


def complete_matching_run(connection, run_id, summary):
    """
    Store the final counts for a successful matching run.
    """
    connection.execute(
        text(
            """
            UPDATE matching_runs
            SET
                finished_at = now(),
                status = 'completed',
                donors_scanned = :donors_scanned,
                open_needs_scanned = :open_needs_scanned,
                giving_history_records = :giving_history_records,
                total_combinations = :total_combinations,
                qualified_matches = :qualified_matches,
                inserted_matches = :inserted_matches,
                updated_matches = :updated_matches,
                not_qualified_matches = :not_qualified_matches,
                skipped_matches = :skipped_matches,
                errors = :errors,
                error_message = NULL
            WHERE run_id = :run_id
            """
        ),
        {
            "run_id": run_id,
            **summary,
        },
    )

    connection.commit()


def fail_matching_run(connection, run_id, error, summary):
    """
    Store the available counts and error for a failed run.
    """
    connection.execute(
        text(
            """
            UPDATE matching_runs
            SET
                finished_at = now(),
                status = 'failed',
                donors_scanned = :donors_scanned,
                open_needs_scanned = :open_needs_scanned,
                giving_history_records = :giving_history_records,
                total_combinations = :total_combinations,
                qualified_matches = :qualified_matches,
                inserted_matches = :inserted_matches,
                updated_matches = :updated_matches,
                not_qualified_matches = :not_qualified_matches,
                skipped_matches = :skipped_matches,
                errors = :errors,
                error_message = :error_message
            WHERE run_id = :run_id
            """
        ),
        {
            "run_id": run_id,
            **summary,
            "error_message": str(error)[:2000],
        },
    )

    connection.commit()


def generate_matches(progress_callback: ProgressCallback = None):
    """
    Generate automatic donor-to-community-need matches.

    A PostgreSQL advisory lock prevents overlapping matching runs.
    Each execution is recorded in matching_runs.

    Confirmed and rejected coordinator decisions continue to be
    protected by the database helper functions.
    """

    def report_progress(stage, message, progress):
        if progress_callback:
            progress_callback(stage, message, progress)

    donors = []
    needs = []
    giving_history = []

    qualified_matches = 0
    inserted_matches = 0
    updated_matches = 0
    not_qualified_matches = 0
    skipped_matches = 0
    errors = 0

    run_id = None
    total_combinations = 0

    # This connection must stay open for the entire run because
    # PostgreSQL advisory locks belong to the database session.
    with engine.connect() as lock_connection:

        if not acquire_matching_lock(lock_connection):
            message = (
                "Another matching-engine run is already in progress. "
                "Please wait for it to finish."
            )

            report_progress(
                "busy",
                message,
                1.0,
            )

            raise RuntimeError(message)

        try:
            run_id = create_matching_run(lock_connection)

            report_progress(
                "loading_donors",
                "Loading donors from the database...",
                0.10,
            )

            donors = get_donors(lock_connection)

            report_progress(
                "loading_needs",
                "Loading open community needs...",
                0.20,
            )

            needs = get_community_needs(lock_connection)

            report_progress(
                "loading_history",
                "Loading donor giving history...",
                0.25,
            )

            giving_history = get_giving_history(lock_connection)

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

            # Matching changes remain atomic.
            # A failure rolls back the entire matching transaction.
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

                            existing_match = match_exists(
                                connection=connection,
                                donor_id=donor["donor_id"],
                                need_id=need["need_id"],
                            )

                            if total_score < 50:
                                skipped_matches += 1

                                if existing_match:
                                    closed_match = mark_match_not_qualified(
                                        connection=connection,
                                        donor_id=donor["donor_id"],
                                        need_id=need["need_id"],
                                        match_score=total_score,
                                        score_breakdown=score_breakdown,
                                    )

                                    if closed_match:
                                        not_qualified_matches += 1

                            else:
                                qualified_matches += 1

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
                                combinations_processed
                                / total_combinations
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

            summary = {
                "donors_scanned": len(donors),
                "open_needs_scanned": len(needs),
                "giving_history_records": len(giving_history),
                "total_combinations": total_combinations,
                "qualified_matches": qualified_matches,
                "inserted_matches": inserted_matches,
                "updated_matches": updated_matches,
                "not_qualified_matches": not_qualified_matches,
                "skipped_matches": skipped_matches,
                "errors": errors,
            }

            complete_matching_run(
                lock_connection,
                run_id,
                summary,
            )

            report_progress(
                "completed",
                "Matching engine completed successfully.",
                1.0,
            )

        except Exception as error:
            if errors == 0:
                errors = 1

            summary = {
                "donors_scanned": len(donors),
                "open_needs_scanned": len(needs),
                "giving_history_records": len(giving_history),
                "total_combinations": total_combinations,
                "qualified_matches": qualified_matches,
                "inserted_matches": inserted_matches,
                "updated_matches": updated_matches,
                "not_qualified_matches": not_qualified_matches,
                "skipped_matches": skipped_matches,
                "errors": errors,
            }

            if run_id is not None:
                try:
                    fail_matching_run(
                        lock_connection,
                        run_id,
                        error,
                        summary,
                    )
                except Exception:
                    # Do not replace the original matching error with
                    # an error from run-history logging.
                    pass

            report_progress(
                "failed",
                "Matching engine failed. Check the application logs for details.",
                1.0,
            )

            raise

        finally:
            release_matching_lock(lock_connection)

    summary["run_id"] = str(run_id)

    print("\n--------------------------------------")
    print(f"Matching run ID: {summary['run_id']}")
    print(f"Donors scanned: {summary['donors_scanned']}")
    print(f"Open needs scanned: {summary['open_needs_scanned']}")
    print(
        "Giving-history records loaded: "
        f"{summary['giving_history_records']}"
    )
    print(
        f"Combinations evaluated: "
        f"{summary['total_combinations']}"
    )
    print(
        f"Qualified matches: "
        f"{summary['qualified_matches']}"
    )
    print(f"Inserted: {summary['inserted_matches']}")
    print(f"Updated: {summary['updated_matches']}")
    print(
        "Marked not qualified: "
        f"{summary['not_qualified_matches']}"
    )
    print(
        "Skipped below score 50: "
        f"{summary['skipped_matches']}"
    )
    print(f"Errors: {summary['errors']}")
    print("--------------------------------------\n")

    return summary


if __name__ == "__main__":
    generate_matches()