import os
import uuid
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file")

engine = create_engine(DATABASE_URL)

csv_path = Path("app/input/GG Transfer Summary(Sheet1).csv")
rejection_log_path = Path("etl/rejection_log.csv")

allowed_channels = {"Sendwave", "Wave", "other"}

df = pd.read_csv(csv_path, skiprows=6)


with engine.connect() as connection:
    result = connection.execute(
        text(
            """
            SELECT donor_id
            FROM donors
            WHERE name = 'Gambia Garden'
            """
        )
    )

    donor = result.fetchone()

    if donor:
        donor_id = donor[0]
        print(f"Found donor_id: {donor_id}")
    else:
        raise Exception("Gambia Garden donor not found.")


clean_rows = []
rejected_rows = []

for index, row in df.iterrows():
    reasons = []

    gift_date = pd.to_datetime(row["Date mm/dd/yr"], errors="coerce")
    if pd.isna(gift_date):
        reasons.append("Invalid date")

    amount = pd.to_numeric(row["Transfer Amount (USD)"], errors="coerce")
    if pd.isna(amount):
        reasons.append("Invalid amount")

    channel = "other"
    if channel not in allowed_channels:
        reasons.append("Invalid channel")

    if reasons:
        rejected_row = row.to_dict()
        rejected_row["rejection_reason"] = "; ".join(reasons)
        rejected_rows.append(rejected_row)
    else:
        clean_rows.append(
            {
                "gift_id": str(uuid.uuid4()),
                "donor_id": donor_id,
                "need_id": None,
                "match_id": None,
                "amount": float(amount),
                "in_kind_desc": None,
                "channel": channel,
                "transaction_ref": str(row["Sending Details"]),
                "impact_note": str(row["Receiving Details"]),
                "gift_date": gift_date,
            }
        )


if rejected_rows:
    rejected_df = pd.DataFrame(rejected_rows)
    rejected_df.to_csv(rejection_log_path, index=False)
    print(f"Rejected rows written to {rejection_log_path}")
else:
    print("No rejected rows.")


with engine.begin() as connection:
    for row in clean_rows:
        connection.execute(
            text(
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
                    :gift_date
                )
                """
            ),
            row,
        )


print(f"Total rows read: {len(df)}")
print(f"Clean rows inserted: {len(clean_rows)}")
print(f"Rejected rows: {len(rejected_rows)}")
print("Import completed successfully.")