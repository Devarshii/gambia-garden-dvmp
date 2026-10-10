
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


def test_only_one_confirmed_match_per_need():
    database_url = os.getenv("TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    # Safety: never run this test against an unexpected database.
    if database_url != "postgresql://dev@localhost:5432/dvmp_test":
        pytest.fail("This test must use the local dvmp_test database")

    engine = create_engine(database_url)

    region_id = str(uuid4())
    category_id = str(uuid4())
    coordinator_id = str(uuid4())
    need_id = str(uuid4())
    donor_1 = str(uuid4())
    donor_2 = str(uuid4())
    match_1 = str(uuid4())
    match_2 = str(uuid4())

    connection = engine.connect()
    transaction = connection.begin()

    try:
        connection.execute(
            text("""
                INSERT INTO regions
                    (region_id, region_code, region_name, country)
                VALUES
                    (:id, :code, 'Test Region', 'Gambia')
            """),
            {"id": region_id, "code": f"TEST-{uuid4().hex[:8]}"},
        )

        connection.execute(
            text("""
                INSERT INTO categories
                    (category_id, category_code, label)
                VALUES
                    (:id, :code, 'Test Category')
            """),
            {"id": category_id, "code": f"TEST-{uuid4().hex[:8]}"},
        )

        connection.execute(
            text("""
                INSERT INTO coordinators
                    (coord_id, name, email, region_id)
                VALUES
                    (:id, 'Test Coordinator', :email, :region_id)
            """),
            {
                "id": coordinator_id,
                "email": f"{uuid4().hex}@example.com",
                "region_id": region_id,
            },
        )

        for donor_id in (donor_1, donor_2):
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
                    (need_id, region_id, category_id,
                     coord_id, village, urgency, status)
                VALUES
                    (:need_id, :region_id, :category_id,
                     :coord_id, 'Test Village', 3, 'open')
            """),
            {
                "need_id": need_id,
                "region_id": region_id,
                "category_id": category_id,
                "coord_id": coordinator_id,
            },
        )

        for match_id, donor_id in (
            (match_1, donor_1),
            (match_2, donor_2),
        ):
            connection.execute(
                text("""
                    INSERT INTO matches
                        (match_id, donor_id, need_id,
                         match_type, status)
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

        connection.execute(
            text("""
                UPDATE matches
                SET status = 'confirmed'
                WHERE match_id = :match_id
            """),
            {"match_id": match_1},
        )

        # A savepoint allows us to catch the expected
        # constraint violation without aborting the
        # entire outer transaction.
        savepoint = connection.begin_nested()

        with pytest.raises(IntegrityError):
            connection.execute(
                text("""
                    UPDATE matches
                    SET status = 'confirmed'
                    WHERE match_id = :match_id
                """),
                {"match_id": match_2},
            )

        savepoint.rollback()

        confirmed_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM matches
                WHERE need_id = :need_id
                  AND status = 'confirmed'
            """),
            {"need_id": need_id},
        ).scalar_one()

        assert confirmed_count == 1

    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()

def test_confirm_match_updates_need_and_rejects_competitors():
    from app.matching.database import confirm_match

    database_url = os.getenv("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not configured")

    if database_url != "postgresql://dev@localhost:5432/dvmp_test":
        pytest.fail("This test requires the local dvmp_test database")

    engine = create_engine(database_url)
    region_id = str(uuid4())
    category_id = str(uuid4())
    coordinator_id = str(uuid4())
    need_id = str(uuid4())
    donor_1 = str(uuid4())
    donor_2 = str(uuid4())
    match_1 = str(uuid4())
    match_2 = str(uuid4())

    connection = engine.connect()
    transaction = connection.begin()

    try:
        connection.execute(
            text("""
                INSERT INTO regions
                    (region_id, region_code, region_name, country)
                VALUES (:id, :code, 'Test Region', 'Gambia')
            """),
            {"id": region_id, "code": f"TEST-{uuid4().hex[:8]}"},
        )

        connection.execute(
            text("""
                INSERT INTO categories
                    (category_id, category_code, label)
                VALUES (:id, :code, 'Test Category')
            """),
            {"id": category_id, "code": f"TEST-{uuid4().hex[:8]}"},
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

        for donor_id in (donor_1, donor_2):
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
                    (need_id, region_id, category_id,
                     coord_id, village, urgency, status)
                VALUES
                    (:need_id, :region_id, :category_id,
                     :coord_id, 'Test Village', 3, 'open')
            """),
            {
                "need_id": need_id,
                "region_id": region_id,
                "category_id": category_id,
                "coord_id": coordinator_id,
            },
        )

        for match_id, donor_id in (
            (match_1, donor_1),
            (match_2, donor_2),
        ):
            connection.execute(
                text("""
                    INSERT INTO matches
                        (match_id, donor_id, need_id,
                         match_type, status)
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

        result = confirm_match(
            connection,
            match_id=match_1,
            coordinator_notes="Approved during integration test",
        )

        assert result is not None
        assert str(result["match_id"]) == match_1

        statuses = connection.execute(
            text("""
                SELECT match_id, status
                FROM matches
                WHERE need_id = :need_id
            """),
            {"need_id": need_id},
        ).fetchall()

        status_by_match = {
            str(row.match_id): row.status
            for row in statuses
        }

        assert status_by_match[match_1] == "confirmed"
        assert status_by_match[match_2] == "rejected"

        need_status = connection.execute(
            text("""
                SELECT status
                FROM community_needs
                WHERE need_id = :need_id
            """),
            {"need_id": need_id},
        ).scalar_one()

        assert need_status == "matched"

        # A second confirmation must be blocked.
        second_result = confirm_match(
            connection,
            match_id=match_2,
        )

        assert second_result is None

        confirmed_count = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM matches
                WHERE need_id = :need_id
                  AND status = 'confirmed'
            """),
            {"need_id": need_id},
        ).scalar_one()

        assert confirmed_count == 1

    finally:
        transaction.rollback()
        connection.close()
        engine.dispose()
