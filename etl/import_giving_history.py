import hashlib
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

NEED_MAPPING_PATH = Path(
    "etl/giving_history_need_mapping.csv"
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


def generate_source_fingerprint(
    donor_id,
    gift_date,
    amount,
    transaction_ref,
    impact_note,
) -> str:
    """
    Generate a deterministic fingerprint for an imported
    financial transaction.

    The same normalized source transaction will always
    produce the same SHA-256 fingerprint.
    """
    normalized_date = pd.Timestamp(
        gift_date
    ).strftime("%Y-%m-%d")

    normalized_amount = f"{float(amount):.2f}"

    normalized_transaction_ref = (
        clean_optional_text(transaction_ref) or ""
    ).lower()

    normalized_impact_note = (
        clean_optional_text(impact_note) or ""
    ).lower()

    fingerprint_source = "|".join(
        [
            str(donor_id),
            normalized_date,
            normalized_amount,
            normalized_transaction_ref,
            normalized_impact_note,
        ]
    )

    return hashlib.sha256(
        fingerprint_source.encode("utf-8")
    ).hexdigest()


def load_need_mapping() -> dict[str, str]:
    """
    Load explicit transaction-to-community-need mappings.

    The mapping CSV must contain:
    transaction_ref,need_id

    Transactions without a mapping remain unlinked.
    """
    if not NEED_MAPPING_PATH.exists():
        return {}

    mapping_dataframe = pd.read_csv(
        NEED_MAPPING_PATH,
        dtype=str,
    )

    required_columns = {
        "transaction_ref",
        "need_id",
    }

    missing_columns = (
        required_columns - set(mapping_dataframe.columns)
    )

    if missing_columns:
        missing_column_list = ", ".join(
            sorted(missing_columns)
        )

        raise ValueError(
            "Need mapping CSV is missing required columns: "
            f"{missing_column_list}"
        )

    mapping = {}

    for _, row in mapping_dataframe.iterrows():
        transaction_ref = clean_optional_text(
            row.get("transaction_ref")
        )

        need_id = clean_optional_text(
            row.get("need_id")
        )

        if not transaction_ref or not need_id:
            continue

        try:
            normalized_need_id = str(
                uuid.UUID(need_id)
            )
        except ValueError as error:
            raise ValueError(
                "Invalid need_id in need mapping for "
                f"transaction_ref '{transaction_ref}': "
                f"{need_id}"
            ) from error

        if transaction_ref in mapping:
            if mapping[transaction_ref] != normalized_need_id:
                raise ValueError(
                    "Conflicting mappings found for "
                    f"transaction_ref '{transaction_ref}'."
                )

        mapping[transaction_ref] = normalized_need_id

    return mapping


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


def validate_need_mapping(
    connection,
    need_mapping: dict[str, str],
):
    """
    Verify that every mapped need_id exists in community_needs.
    """
    if not need_mapping:
        return

    mapped_need_ids = set(need_mapping.values())

    result = connection.execute(
        text(
            """
            SELECT need_id
            FROM community_needs
            """
        )
    )

    existing_need_ids = {
        str(row[0])
        for row in result.fetchall()
    }

    missing_need_ids = (
        mapped_need_ids - existing_need_ids
    )

    if missing_need_ids:
        missing_list = ", ".join(
            sorted(missing_need_ids)
        )

        raise ValueError(
            "The following mapped need_id values do not "
            f"exist in community_needs: {missing_list}"
        )


# ---------------------------------------------------------
# Import logic
# ---------------------------------------------------------

def import_giving_history() -> dict:
    """
    Import giving-history records from the finance CSV.

    Historical transactions can be explicitly linked to
    community needs through giving_history_need_mapping.csv.

    A deterministic source fingerprint is generated for each
    imported transaction. PostgreSQL enforces uniqueness on
    this fingerprint so concurrent imports cannot insert the
    same source transaction twice.
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

    need_mapping = load_need_mapping()

    with engine.connect() as connection:
        donor_id = get_donor_id(connection)

        validate_need_mapping(
            connection,
            need_mapping,
        )

    print(f"Found donor_id: {donor_id}")
    print(
        "Need mappings loaded: "
        f"{len(need_mapping)}"
    )

    clean_rows = []
    rejected_rows = []

    mapped_rows = 0
    unmapped_rows = 0

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

        mapped_need_id = None

        if sending_details:
            mapped_need_id = need_mapping.get(
                sending_details
            )

        if mapped_need_id:
            mapped_rows += 1
        else:
            unmapped_rows += 1

        source_fingerprint = generate_source_fingerprint(
            donor_id=donor_id,
            gift_date=gift_date,
            amount=amount,
            transaction_ref=sending_details,
            impact_note=receiving_details,
        )

        clean_rows.append(
            {
                "gift_id": str(uuid.uuid4()),
                "donor_id": donor_id,
                "need_id": mapped_need_id,
                "match_id": None,
                "amount": float(amount),
                "in_kind_desc": None,
                "channel": channel,
                "transaction_ref": sending_details,
                "impact_note": receiving_details,
                "gift_date": gift_date.to_pydatetime(),
                "source_fingerprint": source_fingerprint,
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
            gift_date,
            source_fingerprint
        )
        VALUES (
            :gift_id,
            :donor_id,
            :need_id,
            :match_id,
            :amount,
            :in_kind_desc,
            :channel,
            :transaction_ref,
            :impact_note,
            :gift_date,
            :source_fingerprint
        )
        ON CONFLICT (source_fingerprint)
        DO NOTHING
        RETURNING gift_id
        """
    )

    with engine.begin() as connection:
        for clean_row in clean_rows:
            result = connection.execute(
                insert_query,
                clean_row,
            )

            inserted_gift_id = (
                result.scalar_one_or_none()
            )

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
        "mapped_rows": mapped_rows,
        "unmapped_rows": unmapped_rows,
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
    print(
        "Rows mapped to needs: "
        f"{summary['mapped_rows']}"
    )
    print(
        "Rows without need mapping: "
        f"{summary['unmapped_rows']}"
    )
    print("--------------------------------------")
    print("Import completed successfully.")
    print()

    return summary


if __name__ == "__main__":
    import_giving_history()