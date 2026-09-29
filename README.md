# Gambia Garden DVMP

Gambia Garden DVMP is a donor-to-community-need matching platform designed to help coordinators connect donors with community needs based on donor preferences, geographic interests, giving capacity, urgency, and historical giving patterns.

The project combines PostgreSQL, Alembic, Python, SQLAlchemy, and Streamlit to provide a structured and reviewable matching workflow.

---

## Features

### Donor and Community Need Management

The PostgreSQL database stores and manages:

- Donors
- Community needs
- Matches
- Giving history
- Coordinators
- Categories
- Regions
- Matching run history

Database changes are managed through Alembic migrations.

### Matching Engine

The matching engine evaluates donors against open community needs using a weighted scoring model.

The score considers:

- Preferred cause/category
- Preferred region
- Giving capacity
- Need priority/urgency
- Relevant giving history

Each generated match stores both the total score and a score breakdown for transparency.

### Coordinator Review

The Streamlit coordinator interface allows users to:

- View open community needs
- Filter needs by region, category, urgency, and status
- View donor information
- Run the matching engine
- Review proposed matches
- Inspect score breakdowns
- Confirm or reject proposed matches

Confirmed and rejected coordinator decisions are protected from later matching-engine recalculations.

### Giving History Import

Historical transfer data can be imported through the ETL pipeline.

The importer includes:

- Donor lookup
- Transfer-channel validation
- Rejection logging
- Optional mapping of historical transactions to community needs
- Deterministic source fingerprints
- Database-level duplicate protection
- Idempotent imports

Running the same source import multiple times does not create duplicate giving-history records.

### Matching Run Safety and Observability

Matching runs are tracked so that execution can be monitored and audited.

Run information includes metrics such as:

- Donors scanned
- Open needs scanned
- Giving-history records processed
- Donor/need combinations evaluated
- Qualified matches
- Inserted matches
- Updated matches
- Skipped matches
- Errors

Concurrency protection prevents overlapping matching-engine runs.

### Automated Testing and CI

The project includes automated tests for:

- Cause scoring
- Region scoring
- Giving-capacity scoring
- Priority scoring
- Giving-history scoring
- Complete match-score calculation
- Protection of confirmed/rejected match decisions

GitHub Actions automatically runs the test suite on pushes and pull requests.

---

## Technology Stack

- Python
- PostgreSQL
- SQLAlchemy
- Alembic
- Streamlit
- Supabase
- pandas
- pytest
- GitHub Actions

---

## Project Structure

```text
gambia-garden-dvmp/
├── .github/
│   └── workflows/
│       └── tests.yml
├── app/
│   ├── input/
│   ├── matching/
│   │   ├── database.py
│   │   ├── generate_matches.py
│   │   └── scoring.py
│   └── main.py
├── docs/
│   ├── Data_Dictionary.md
│   └── finance_spreadsheet_mapping.md
├── etl/
│   ├── import_giving_history.py
│   └── giving_history_need_mapping.csv
├── migrations/
│   └── versions/
├── tests/
│   ├── test_match_decisions.py
│   └── test_scoring.py
├── alembic.ini
├── requirements.txt
└── README.md