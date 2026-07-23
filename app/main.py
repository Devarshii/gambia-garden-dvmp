import sys
from pathlib import Path

# ---------------------------------------------------------
# Add the project root to Python's import path
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.matching.generate_matches import engine


# ---------------------------------------------------------
# Streamlit page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Gambia Garden DVMP",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Database connection check
# ---------------------------------------------------------

def check_database_connection():
    """
    Test the database connection.
    """
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


# ---------------------------------------------------------
# Pages
# ---------------------------------------------------------

def show_open_needs():
    st.title("📋 Open Needs")

    st.write(
        "View community needs that are currently open "
        "and available for donor matching."
    )

    st.info(
        "Open community needs will appear here in the next task."
    )


def show_donor_profile():
    st.title("👤 Donor Profile")

    st.write(
        "Search and review donor information including "
        "giving capacity, preferred causes and preferred regions."
    )

    st.info(
        "Donor profiles will appear here in the next task."
    )


def show_match_review():
    st.title("🤝 Match Review")

    st.write(
        "Review automatically generated donor-to-community matches."
    )

    st.info(
        "Generated matches will appear here in the next task."
    )


# ---------------------------------------------------------
# Main App
# ---------------------------------------------------------

def main():

    try:
        check_database_connection()

    except SQLAlchemyError:
        st.error(
            "Unable to connect to the database.\n\n"
            "Please verify that PostgreSQL is running and "
            "your DATABASE_URL in the .env file is correct."
        )
        st.stop()

    except Exception as e:
        st.error(f"Unexpected database error:\n\n{e}")
        st.stop()

    st.sidebar.title("🌱 Gambia Garden DVMP")
    st.sidebar.success("Database Connected")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Open Needs",
            "Donor Profile",
            "Match Review",
        ],
    )

    if page == "Open Needs":
        show_open_needs()

    elif page == "Donor Profile":
        show_donor_profile()

    elif page == "Match Review":
        show_match_review()


if __name__ == "__main__":
    main()