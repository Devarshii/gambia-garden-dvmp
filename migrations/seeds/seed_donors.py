import os
import uuid

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set.")

engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    conn.execute(
        text("""
            INSERT INTO donors (
                donor_id,
                name,
                email,
                location,
                interests,
                giving_capacity,
                preferred_causes,
                preferred_regions
            )
            VALUES (
                :donor_id,
                :name,
                :email,
                :location,
                :interests,
                :giving_capacity,
                :preferred_causes,
                :preferred_regions
            )
            ON CONFLICT (email) DO NOTHING;
        """),
        {
            "donor_id": str(uuid.uuid4()),
            "name": "Gambia Garden",
            "email": "gambiagardens@gmail.com",
            "location": "Zug, Switzerland",
            "interests": ["Community Development"],
            "giving_capacity": None,
            "preferred_causes": ["All Categories"],
            "preferred_regions": ["All Regions of The Gambia"],
        },
    )

print("✅ Gambia Garden donor seeded successfully.")