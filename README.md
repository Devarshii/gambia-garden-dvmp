# Gambia Garden DVMP

## Overview

The **Gambia Garden Donor-Village Matching Platform (DVMP)** is a data-driven platform designed to connect donors with community needs through an intelligent matching system. The project provides a structured PostgreSQL database with version-controlled Alembic migrations and serves as the backend foundation for future analytics, ETL pipelines, and a Streamlit-based application.

---

## Project Objectives

* Build a scalable PostgreSQL database for donor management.
* Track community needs and donation history.
* Support intelligent donor-to-community matching.
* Maintain version-controlled database migrations using Alembic.
* Ensure database integrity through foreign keys and CHECK constraints.
* Optimize query performance using indexes.
* Provide a foundation for future analytics, reporting, and a Streamlit application.

---

## Tech Stack

| Technology   | Purpose                       |
| ------------ | ----------------------------- |
| Python 3.12  | Programming Language          |
| PostgreSQL   | Relational Database           |
| SQLAlchemy   | ORM                           |
| Alembic      | Database Migration Management |
| Pandas       | Data Processing               |
| Streamlit    | Future Web Application        |
| Git & GitHub | Version Control               |

---

## Repository Structure

```text
gambia-garden-dvmp/
│
├── app/                  # Future Streamlit application
├── docs/                 # Documentation (ERD, Data Dictionary, README)
├── etl/                  # Data migration and ETL scripts
├── migrations/
│   ├── versions/         # Alembic migration files
│   └── seeds/            # Seed scripts
├── tests/                # Data quality and integrity tests
├── README.md
├── requirements.txt
├── alembic.ini
└── .env.example
```

---

## Database Schema

The database consists of **7 tables**.

### Core Tables

* donors
* community_needs
* matches
* giving_history

### Supporting Tables

* regions
* categories
* coordinators

The complete Entity Relationship Diagram (ERD) and Data Dictionary are available in the **docs/** directory.

---

## Database Migrations

The schema is managed using **Alembic** to ensure version-controlled database changes.

### Migration 001

Created supporting tables:

* regions
* categories
* coordinators

### Migration 002

Created core entities:

* donors
* community_needs

### Migration 003

Created:

* matches
* giving_history

Also implemented:

* Foreign key relationships
* CHECK constraints
* Query optimization indexes

---

## Database Features

### Primary Keys

Every table uses UUID primary keys.

### Foreign Keys

Relationships are enforced between:

* coordinators → regions
* community_needs → regions
* community_needs → categories
* community_needs → coordinators
* matches → donors
* matches → community_needs
* giving_history → donors
* giving_history → community_needs
* giving_history → matches

### CHECK Constraints

Implemented validation for:

* Community need urgency (1–5)
* Community need status (`open`, `matched`, `fulfilled`)
* Match type (`manual`, `auto`)
* Donation channel (`Sendwave`, `Wave`, `other`)

### Indexes

Indexes were created to improve query performance.

**Community Needs**

* region_id
* category_id
* urgency
* status

**Matches**

* donor_id
* need_id
* status

**Giving History**

* donor_id
* need_id

---

## Environment Setup

### Clone the Repository

```bash
git clone https://github.com/Devarshii/gambia-garden-dvmp.git
cd gambia-garden-dvmp
```

### Create a Virtual Environment

```bash
python -m venv venv
```

### Activate the Environment

Windows

```bash
venv\Scripts\activate
```

macOS / Linux

```bash
source venv/bin/activate
```

### Install Dependencies

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

3. Create a `.env` file in the project root and configure your PostgreSQL connection:

```env
DATABASE_URL=postgresql://<username>:<password>@localhost:5432/gambia_garden_dvmp
```

4. Apply all database migrations:

```bash
alembic upgrade head
```

5. Verify the current migration version:

```bash
alembic current
```
---

## Current Project Status

* GitHub repository initialized
* PostgreSQL configured
* Alembic configured
* Python virtual environment created
* Project dependencies installed
* Environment variables configured
* Three Alembic migrations completed
* Seven database tables implemented
* Primary keys configured
* Foreign key relationships implemented
* CHECK constraints implemented
* Database indexes created
* Entity Relationship Diagram completed
* Data Dictionary completed
* Migration verification completed
* Constraint validation completed

---

## Verification

The following validations have been successfully performed:

* All migrations applied successfully using `alembic upgrade head`
* Migration version verified using `alembic current`
* All tables successfully created
* Foreign key constraints verified
* CHECK constraints verified
* Indexes verified
* Invalid inserts correctly rejected by PostgreSQL

---

## Future Development

* SQLAlchemy ORM models
* ETL pipeline
* Seed data generation
* Streamlit dashboard
* Matching engine implementation
* Analytics dashboard
* Data quality automation
* Unit and integration tests

---

## Author

Devarshi Trivedi

