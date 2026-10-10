
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text

from app.matching.database import confirm_match


TEST_URL = "postgresql://dev@localhost:5432/dvmp_test"


def test_simultaneous_match_confirmations():
    database_url = os.getenv("TEST_DATABASE_URL")

    if database_url != TEST_URL:
        pytest.skip("Requires the local dvmp_test database")

    engine = create_engine(
        database_url,
        pool_size=3,
        max_overflow=0,
        connect_args={"connect_timeout": 5},
    )

    region_id = str(uuid4())
    category_id = str(uuid4())
    coordinator_id = str(uuid4())
    need_id = str(uuid4())
    donor_ids = [str(uuid4()), str(uuid4())]
    match_ids = [str(uuid4()), str(uuid4())]

    try:
        # Create temporary records visible to both connections.
        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO regions
                        (region_id, region_code, region_name, country)
                    VALUES (:id, :code, 'Concurrency Test', 'Gambia')
                """),
                {"id": region_id, "code": f"T-{uuid4().hex[:10]}"},
            )

            connection.execute(
                text("""
                    INSERT INTO categories
                        (category_id, category_code, label)
                    VALUES (:id, :code, 'Concurrency Test')
                """),
                {"id": category_id, "code": f"T-{uuid4().hex[:10]}"},
            )

            connection.execute(
                text("""
                    INSERT INTO coordinators
                        (coord_id, name, email, region_id)
                    VALUES (:id, 'Test Coordinator', :email, :region_id)
                """),
                {
                    "id": coordinator_id,
                    "email": f"{uuid4().hex}@example.com",
                    "region_id": region_id,
                },
            )

            for donor_id in donor_ids:
                connection.execute(
                    text("""
                        INSERT INTO donors (donor_id, name, email)
                        VALUES (:id, 'Test Donor', :email)
                    """),
                    {
                        "id": donor_id,
                        "email": f"{uuid4().hex}@example.com",
                    },
                )

            connection.execute(
                text("""
                    INSERT INTO community_needs
                        (need_id, region_id, category_id, coord_id,
                         village, urgency, status)
                    VALUES
                        (:need_id, :region_id, :category_id, :coord_id,
                         'Test Village', 3, 'open')
                """),
                {
                    "need_id": need_id,
                    "region_id": region_id,
                    "category_id": category_id,
                    "coord_id": coordinator_id,
                },
            )

            for match_id, donor_id in zip(match_ids, donor_ids):
                connection.execute(
                    text("""
                        INSERT INTO matches
                            (match_id, donor_id, need_id, match_type, status)
                        VALUES
                            (:match_id, :donor_id, :need_id,
                             'manual', 'proposed')
                    """),
                    {
                        "match_id": match_id,
                        "donor_id": donor_id,
                        "need_id": need_id,
                    },
                )

        barrier = threading.Barrier(2)

        def attempt_confirmation(match_id):
            barrier.wait(timeout=10)

            with engine.begin() as connection:
                connection.execute(
                    text("SET LOCAL lock_timeout = '10s'")
                )
                return confirm_match(connection, match_id)

        # Both workers attempt confirmation simultaneously.
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(attempt_confirmation, match_id)
                for match_id in match_ids
            ]
            results = [
                future.result(timeout=15)
                for future in futures
            ]

        # Exactly one confirmation should succeed.
        assert sum(result is not None for result in results) == 1

        with engine.connect() as connection:
            confirmed = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM matches
                    WHERE need_id = :need_id
                      AND status = 'confirmed'
                """),
                {"need_id": need_id},
            ).scalar_one()

            rejected = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM matches
                    WHERE need_id = :need_id
                      AND status = 'rejected'
                """),
                {"need_id": need_id},
            ).scalar_one()

            need_status = connection.execute(
                text("""
                    SELECT status
                    FROM community_needs
                    WHERE need_id = :need_id
                """),
                {"need_id": need_id},
            ).scalar_one()

        assert confirmed == 1
        assert rejected == 1
        assert need_status == "matched"

    finally:
        # Remove only this test's temporary records.
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM matches WHERE need_id = :id"),
                {"id": need_id},
            )
            connection.execute(
                text("DELETE FROM community_needs WHERE need_id = :id"),
                {"id": need_id},
            )
            connection.execute(
            text("DELETE FROM donors WHERE donor_id = ANY(CAST(:ids AS UUID[]))"),
             {"ids": donor_ids},     
                    )
            connection.execute(
                text("DELETE FROM coordinators WHERE coord_id = :id"),
                {"id": coordinator_id},
            )
            connection.execute(
                text("DELETE FROM categories WHERE category_id = :id"),
                {"id": category_id},
            )
            connection.execute(
                text("DELETE FROM regions WHERE region_id = :id"),
                {"id": region_id},
            )

        engine.dispose()
