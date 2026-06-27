import os
import uuid
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found. Please check your .env file.")

engine = create_engine(DATABASE_URL)

CATEGORIES = [
    ("SCHOOL_MATERIALS", "School Materials", "Supplies needed for schools and students"),
    ("CLEAN_WATER", "Clean Water", "Water access, wells, filters, and sanitation support"),
    ("MEDICAL_SUPPLIES", "Medical Supplies", "Healthcare and clinic-related supplies"),
    ("AGRICULTURAL_TOOLS", "Agricultural Tools", "Tools and equipment for farming"),
    ("SHELTER_REPAIR", "Shelter Repair", "Housing and building repair needs"),
    ("FOOD_SECURITY", "Food Security", "Food access and nutrition support"),
    ("WOMENS_HEALTH", "Women’s Health", "Women’s health and maternal care needs"),
    ("EARLY_CHILDHOOD", "Early Childhood", "Support for young children and early learning"),
]

with engine.begin() as conn:
    for code, label, description in CATEGORIES:
        conn.execute(
            text("""
                INSERT INTO categories (
                    category_id,
                    category_code,
                    label,
                    description,
                    is_active
                )
                SELECT
                    :category_id,
                    :category_code,
                    :label,
                    :description,
                    :is_active
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM categories
                    WHERE category_code = :category_code
                );
            """),
            {
                "category_id": str(uuid.uuid4()),
                "category_code": code,
                "label": label,
                "description": description,
                "is_active": True,
            },
        )

print("✅ Categories seeded successfully!")