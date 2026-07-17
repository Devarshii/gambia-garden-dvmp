import os

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


def generate_matches():
    """
    Generate automatic donor-to-community-need matches.

    Qualified matches are inserted when new and updated when
    the donor-to-need combination already exists.
    """
    with engine.connect() as connection:
        donors = get_donors(connection)
        needs = get_community_needs(connection)

    print(f"\nDonors found: {len(donors)}")
    print(f"Open community needs found: {len(needs)}\n")

    qualified_matches = 0
    inserted_matches = 0
    updated_matches = 0
    skipped_matches = 0

    with engine.begin() as connection:
        for donor in donors:
            for need in needs:
                score_breakdown = calculate_match_score(
                    preferred_causes=donor["preferred_causes"],
                    preferred_regions=donor["preferred_regions"],
                    giving_capacity=donor["giving_capacity"],
                    category_name=need["category_name"],
                    region_name=need["region_name"],
                    requested_amount=need["requested_amount"],
                    priority=need["priority"],
                )

                total_score = score_breakdown["total_score"]

                if total_score < 50:
                    skipped_matches += 1
                    continue

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
                    )

                    updated_matches += 1

                    print(
                        f"Updated match | "
                        f"Donor: {donor['name']} | "
                        f"Need: {need['need_name']} | "
                        f"Score: {total_score}"
                    )
                else:
                    insert_match(
                        connection=connection,
                        donor_id=donor["donor_id"],
                        need_id=need["need_id"],
                        match_score=total_score,
                    )

                    inserted_matches += 1

                    print(
                        f"New match | "
                        f"Donor: {donor['name']} | "
                        f"Need: {need['need_name']} | "
                        f"Score: {total_score}"
                    )

                print(
                    f"  Cause: {score_breakdown['cause_score']}, "
                    f"Region: {score_breakdown['region_score']}, "
                    f"Capacity: {score_breakdown['capacity_score']}, "
                    f"Priority: {score_breakdown['priority_score']}, "
                    f"History: {score_breakdown['history_score']}"
                )

    print("\n--------------------------------------")
    print(f"Donors scanned: {len(donors)}")
    print(f"Open needs scanned: {len(needs)}")
    print(f"Qualified matches: {qualified_matches}")
    print(f"Inserted: {inserted_matches}")
    print(f"Updated: {updated_matches}")
    print(f"Skipped below score 50: {skipped_matches}")
    print("--------------------------------------\n")


if __name__ == "__main__":
    generate_matches()