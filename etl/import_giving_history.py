import os
import uuid
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

engine = create_engine(DATABASE_URL)

CSV_PATH = Path(
    "app/input/GG Transfer Summary(Sheet1).csv"
)

REJECTION_LOG_PATH = Path(
    "etl/rejection_log.csv"
)

ALLOWED_CHANNELS = {
    "Sendwave",
    "Wave",
    "other",
}


# ---------------------------------------------------------
# Cleaning helpers
# ---------------------------------------------------------

def clean_optional_text(value: Any) -> Optional[str]:
    """
    Convert a spreadsheet value into clean text.

    Missing values, blank strings, and textual NaN values
    are converted to None so PostgreSQL stores NULL.
    """
    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    cleaned_value = str(value).strip()

    if not cleaned_value:
        return None

    if cleaned_value.lower() in {
        "nan",
        "none",
        "null",
        "nat",
    }:
        return None

    return cleaned_value


def detect_channel(*values: Any) -> str:
    """
    Detect the transaction channel from spreadsheet text.

    Sendwave is checked before Wave because the word
    'wave' also appears inside 'sendwave'.
    """
    combined_text = " ".join(
        value
        for value in (
            clean_optional_text(item)
            for item in values
        )
        if value
    ).lower()

    if "sendwave" in combined_text:
        return "Sendwave"

    if "wave" in combined_text:
        return "Wave"

    return "other"


def get_donor_id(connection):
    """
    Retrieve the Gambia Garden donor.

    The query supports both the singular and plural versions
    of the donor name.
    """
    result = connection.execute(
        text(
            """
            SELECT donor_id
            FROM donors
            WHERE LOWER(TRIM(name)) IN (
                'gambia garden',
                'gambia gardens'
            )
            ORDER BY
                CASE
                    WHEN LOWER(TRIM(name)) = 'gambia garden'
                        THEN 1
                    ELSE 2
                END
            LIMIT 1
            """
        )
    )

    donor = result.fetchone()

    if not donor:
        raise RuntimeError(
            "Gambia Garden donor was not found."
        )

    return donor[0]


# ---------------------------------------------------------
# Import logic
# ---------------------------------------------------------

def import_giving_history() -> dict:
    """
    Import giving-history records from the finance CSV.

    The import is idempotent: an existing record with the
    same donor, date, amount, transaction reference, and
    impact note is not inserted again.
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"Finance CSV was not found: {CSV_PATH}"
        )

    dataframe = pd.read_csv(
        CSV_PATH,
        skiprows=6,
    )

    required_columns = {
        "Date mm/dd/yr",
        "Transfer Amount (USD)",
        "Sending Details",
        "Receiving Details",
    }

    missing_columns = (
        required_columns - set(dataframe.columns)
    )

    if missing_columns:
        missing_column_list = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "The finance CSV is missing required columns: "
            f"{missing_column_list}"
        )

    with engine.connect() as connection:
        donor_id = get_donor_id(connection)

    print(f"Found donor_id: {donor_id}")

    clean_rows = []
    rejected_rows = []

    for row_number, row in dataframe.iterrows():
        reasons = []

        gift_date = pd.to_datetime(
            row.get("Date mm/dd/yr"),
            errors="coerce",
        )

        if pd.isna(gift_date):
            reasons.append("Invalid or missing date")

        amount = pd.to_numeric(
            row.get("Transfer Amount (USD)"),
            errors="coerce",
        )

        if pd.isna(amount):
            reasons.append("Invalid or missing amount")
        elif float(amount) <= 0:
            reasons.append(
                "Amount must be greater than zero"
            )

        sending_details = clean_optional_text(
            row.get("Sending Details")
        )

        receiving_details = clean_optional_text(
            row.get("Receiving Details")
        )

        channel = detect_channel(
            sending_details,
            receiving_details,
        )

        if channel not in ALLOWED_CHANNELS:
            reasons.append("Invalid channel")

        if reasons:
            rejected_row = {
                column: clean_optional_text(value)
                for column, value in row.to_dict().items()
            }

            rejected_row["source_row_number"] = (
                row_number + 8
            )

            rejected_row["rejection_reason"] = (
                "; ".join(reasons)
            )

            rejected_rows.append(rejected_row)
            continue

        clean_rows.append(
            {
                "gift_id": str(uuid.uuid4()),
                "donor_id": donor_id,
                "need_id": None,
                "match_id": None,
                "amount": float(amount),
                "in_kind_desc": None,
                "channel": channel,
                "transaction_ref": sending_details,
                "impact_note": receiving_details,
                "gift_date": gift_date.to_pydatetime(),
            }
        )

    # Ensure the output directory exists.
    REJECTION_LOG_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if rejected_rows:
        rejected_dataframe = pd.DataFrame(
            rejected_rows
        )

        rejected_dataframe.to_csv(
            REJECTION_LOG_PATH,
            index=False,
        )

        print(
            "Rejected rows written to "
            f"{REJECTION_LOG_PATH}"
        )
    else:
        # Remove an obsolete rejection log from a previous run.
        if REJECTION_LOG_PATH.exists():
            REJECTION_LOG_PATH.unlink()

        print("No rejected rows.")

    inserted_rows = 0
    duplicate_rows = 0

    insert_query = text(
        """
        INSERT INTO giving_history (
            gift_id,
            donor_id,
            need_id,
            match_id,
            amount,
            in_kind_desc,
            channel,
            transaction_ref,
            impact_note,
            gift_date
        )
        SELECT
            :gift_id,
            :donor_id,
            :need_id,
            :match_id,
            :amount,
            :in_kind_desc,
            :channel,
            :transaction_ref,
            :impact_note,
            :gift_date
        WHERE NOT EXISTS (
            SELECT 1
            FROM giving_history existing
            WHERE existing.donor_id = :donor_id
              AND existing.amount = :amount
              AND existing.gift_date = :gift_date
              AND existing.transaction_ref
                    IS NOT DISTINCT FROM :transaction_ref
              AND existing.impact_note
                    IS NOT DISTINCT FROM :impact_note
        )
        RETURNING gift_id
        """
    )

    with engine.begin() as connection:
        for clean_row in clean_rows:
            result = connection.execute(
                insert_query,
                clean_row,
            )

            inserted_gift_id = result.scalar_one_or_none()

            if inserted_gift_id:
                inserted_rows += 1
            else:
                duplicate_rows += 1

    summary = {
        "total_rows_read": len(dataframe),
        "valid_rows": len(clean_rows),
        "inserted_rows": inserted_rows,
        "duplicate_rows_skipped": duplicate_rows,
        "rejected_rows": len(rejected_rows),
    }

    print()
    print("--------------------------------------")
    print(
        "Total rows read: "
        f"{summary['total_rows_read']}"
    )
    print(
        "Valid rows processed: "
        f"{summary['valid_rows']}"
    )
    print(
        "New rows inserted: "
        f"{summary['inserted_rows']}"
    )
    print(
        "Existing duplicates skipped: "
        f"{summary['duplicate_rows_skipped']}"
    )
    print(
        "Rejected rows: "
        f"{summary['rejected_rows']}"
    )
    print("--------------------------------------")
    print("Import completed successfully.")
    print()

    return summary


if __name__ == "__main__":
    import_giving_history()