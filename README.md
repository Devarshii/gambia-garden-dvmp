# Gambia Garden DVMP

## Overview

The Gambia Garden Donor-Village Matching Platform (DVMP) is a data-driven platform designed to connect donors with community needs through an intelligent matching system. The project provides a structured PostgreSQL database with Alembic migrations and serves as the backend foundation for future analytics and a Streamlit-based application.

---

## Project Objectives

- Build a scalable PostgreSQL database for donor management.
- Track community needs and donation history.
- Support intelligent donor-to-community matching.
- Maintain version-controlled database migrations using Alembic.
- Provide a foundation for future analytics and reporting.

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.12 | Programming Language |
| PostgreSQL | Relational Database |
| SQLAlchemy | ORM |
| Alembic | Database Migration Management |
| Pandas | Data Processing |
| Streamlit | Future Web Application |
| Git & GitHub | Version Control |

---

## Repository Structure

```
gambia-garden-dvmp/
│
├── app/                  # Future Streamlit application
├── docs/                 # Documentation (ERD, Data Dictionary, README)
├── etl/                  # Data migration and ETL scripts
├── migrations/           # Alembic migration files
│   ├── versions/
│   └── seeds/
├── tests/                # Data quality and integrity tests
├── README.md
├── requirements.txt
└── alembic.ini
```

---

## Database Schema

The database is designed around the following entities:

### Core Tables

- Donors
- Community_Needs
- Matches
- Giving_History

### Supporting Tables

- Coordinators
- Categories
- Regions

The complete Entity Relationship Diagram (ERD) is available in the `docs/` directory.

---

## Environment Setup

### Clone the repository

```bash
git clone https://github.com/Devarshii/gambia-garden-dvmp.git
cd gambia-garden-dvmp
```

### Create a virtual environment

```bash
python -m venv venv
```

### Activate the environment

**Windows**

```bash
venv\Scripts\activate
```

**macOS/Linux**

```bash
source venv/bin/activate
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## Database Configuration

1. Install PostgreSQL.
2. Create a database named:

```
gambia_garden_dvmp
```

3. Update `alembic.ini` with your PostgreSQL credentials.

4. Verify the connection:

```bash
python -m alembic current
```

---

## Current Project Status

- GitHub repository initialized
- PostgreSQL configured
- Alembic configured
- Python virtual environment created
- Project dependencies installed
- Database connection verified

---

## Future Development

- SQLAlchemy ORM models
- Initial Alembic migrations
- Seed data scripts
- Streamlit dashboard
- Data quality tests
- ETL pipeline
