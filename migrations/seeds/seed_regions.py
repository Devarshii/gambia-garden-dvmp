import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found. Please check your .env file.")

engine = create_engine(DATABASE_URL)

REGIONS = [
    ("BANJUL", "Banjul", "The capital city of The Gambia"),
    ("KANIFING", "Kanifing", "Kanifing Municipality"),
    ("BRIKAMA", "Brikama", "West Coast Region"),
    ("MANSAKONKO", "Mansakonko", "Lower River Region"),
    ("KEREWAN", "Kerewan", "North Bank Region"),
    ("KUNTAUR", "Kuntaur", "Central River Region North"),
    ("JANJANBUREH", "Janjanbureh", "Central River Region South"),
    ("BASSE", "Basse", "Upper River Region"),
]

with engine.begin() as conn:
    for code, name, notes in REGIONS:
        conn.execute(
            text("""
                INSERT INTO regions (
                    region_id,
                    region_code,
                    region_name,
                    country,
                    notes
                )
                SELECT
                    :region_id,
                    :region_code,
                    :region_name,
                    :country,
                    :notes
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM regions
                    WHERE region_code = :region_code
                );
            """),
            {
                "region_id": str(uuid.uuid4()),
                "region_code": code,
                "region_name": name,
                "country": "The Gambia",
                "notes": notes,
            },
        )

print("✅ Regions seeded successfully!")