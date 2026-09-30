# Gambia Garden DVMP - Data Dictionary

## Overview

This document describes the database tables, fields, constraints, and relationships used in the Gambia Garden Donor-Village Matching Platform (DVMP).

It reflects the current database schema managed through Alembic migrations and should be updated whenever the schema changes.

---

## Design Notes

### total_given Design Note

The `total_given` value is not stored in the `donors` table.

Instead, total donor giving is calculated from the `giving_history` table:

```sql
SELECT donor_id, SUM(amount) AS total_given
FROM giving_history
GROUP BY donor_id;
```

This avoids storing duplicate derived data and keeps donation totals based on the underlying giving records.

### preferred_regions Design Note

The `preferred_regions` field in the `donors` table is stored as a `TEXT[]` array rather than foreign key references to the `regions` table.

This is a current design simplification. It may later be normalized into a donor-region relationship table if matching requirements become more complex.

### Giving History Linkage

Imported finance records may initially exist without a known community need or match.

For this reason, `giving_history.need_id` and `giving_history.match_id` are nullable.

When an imported transfer can be mapped to a community need, the ETL mapping process can populate the appropriate relationship so that the record can contribute to need-level historical matching calculations.

### Finance Import Idempotency

Each imported finance record can include a deterministic `source_fingerprint`.

The fingerprint identifies the source transaction and is protected by a database uniqueness constraint. This allows repeated or concurrent imports to avoid inserting the same source transaction more than once.

### Match Decision Preservation

Confirmed or rejected matches represent coordinator decisions.

Once a match reaches a final coordinator decision, later matching-engine recalculations must not overwrite the score and score breakdown associated with that decision.

### Matching Run Tracking

Each matching-engine execution is recorded in the `matching_runs` table.

This provides run-level observability, including start and finish times, status, processing counts, errors, and error details.

The matching engine also uses a database advisory lock to prevent overlapping matching runs from separate application sessions.

---

# Table: regions

Stores geographic regions used for matching community needs with donors and coordinators.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| region_id | UUID | Yes | Primary Key | Unique identifier for each region. |
| region_code | VARCHAR(50) | Yes | NOT NULL | Short code used to identify the region. |
| region_name | VARCHAR(100) | Yes | NOT NULL | Full name of the region. |
| country | VARCHAR(100) | Yes | NOT NULL | Country where the region is located. |
| notes | TEXT | No | Nullable | Optional notes about the region. |

---

# Table: categories

Stores categories used to classify community needs.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| category_id | UUID | Yes | Primary Key | Unique identifier for each category. |
| category_code | VARCHAR(50) | Yes | NOT NULL, UNIQUE | Short unique code for the category. |
| label | VARCHAR(100) | Yes | NOT NULL | Human-readable category name. |
| description | TEXT | No | Nullable | Optional explanation of the category. |
| is_active | BOOLEAN | Yes | NOT NULL, default TRUE | Indicates whether the category is currently active. |

---

# Table: coordinators

Stores coordinators who manage community needs within assigned regions.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| coord_id | UUID | Yes | Primary Key | Unique identifier for each coordinator. |
| name | VARCHAR(100) | Yes | NOT NULL | Full name of the coordinator. |
| email | VARCHAR(150) | Yes | NOT NULL, UNIQUE | Coordinator email address. |
| phone | VARCHAR(30) | No | Nullable | Optional phone number. |
| region_id | UUID | Yes | Foreign Key to regions.region_id | Region assigned to the coordinator. |
| is_active | BOOLEAN | Yes | NOT NULL, default TRUE | Indicates whether the coordinator is active. |
| created_at | TIMESTAMP | Yes | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the coordinator record was created. |

---

# Table: donors

Stores donor profile information, interests, giving capacity, and matching preferences.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| donor_id | UUID | Yes | Primary Key | Unique identifier for each donor. |
| name | VARCHAR(150) | Yes | NOT NULL | Full name of the donor. |
| email | VARCHAR(150) | Yes | NOT NULL, UNIQUE | Donor email address. |
| location | VARCHAR(150) | No | Nullable | Donor location. |
| interests | TEXT[] | No | Nullable | Donor interest areas. |
| giving_capacity | NUMERIC(12,2) | No | Nullable | Estimated donor giving capacity. |
| preferred_causes | TEXT[] | No | Nullable | Causes the donor prefers to support. |
| preferred_regions | TEXT[] | No | Nullable | Regions the donor prefers to support. |
| created_at | TIMESTAMP | Yes | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the donor was created. |
| updated_at | TIMESTAMP | Yes | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the donor was last updated. |

---

# Table: community_needs

Stores needs submitted by communities, including region, category, urgency, workflow status, cost, and coordinator information.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| need_id | UUID | Yes | Primary Key | Unique identifier for each community need. |
| region_id | UUID | Yes | Foreign Key to regions.region_id | Region where the need exists. |
| category_id | UUID | Yes | Foreign Key to categories.category_id | Category of the need. |
| coord_id | UUID | Yes | Foreign Key to coordinators.coord_id | Coordinator responsible for the need. |
| village | VARCHAR(150) | Yes | NOT NULL | Village where the need is located. |
| urgency | INTEGER | Yes | NOT NULL, CHECK 1 to 5 | Urgency rating from 1 to 5. |
| status | VARCHAR(50) | Yes | NOT NULL, default 'open', CHECK open/matched/fulfilled | Current workflow status. |
| description | TEXT | No | Nullable | Detailed explanation of the community need. |
| photo_urls | TEXT[] | No | Nullable | Optional photo URLs associated with the need. |
| estimated_cost | NUMERIC(12,2) | No | Nullable | Estimated cost required to fulfill the need. |
| coordinator_notes | TEXT | No | Nullable | Internal notes recorded by the coordinator. |
| created_at | TIMESTAMP | Yes | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the need was created. |
| resolved_at | TIMESTAMP | No | Nullable | Date and time when the need was resolved. |

Allowed values:

* `urgency`: 1, 2, 3, 4, 5
* `status`: `open`, `matched`, `fulfilled`

---

# Table: matches

Stores donor-to-community-need match records created manually or by the matching engine.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| match_id | UUID | Yes | Primary Key | Unique identifier for each match. |
| donor_id | UUID | Yes | Foreign Key to donors.donor_id | Donor involved in the match. |
| need_id | UUID | Yes | Foreign Key to community_needs.need_id | Community need involved in the match. |
| match_date | TIMESTAMP | Yes | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the match was created. |
| match_type | VARCHAR(50) | Yes | NOT NULL, CHECK manual/auto | Indicates whether the match was created manually or automatically. |
| match_score | NUMERIC(5,2) | No | Nullable | Calculated match score. |
| score_breakdown | JSONB | No | Nullable | Component-level explanation of the calculated match score. |
| status | VARCHAR(50) | No | Nullable | Current coordinator/matching workflow status. |
| coordinator_notes | TEXT | No | Nullable | Optional notes from the coordinator. |
| confirmed_at | TIMESTAMP | No | Nullable | Date and time when the match was confirmed. |

Allowed `match_type` values:

* `manual`
* `auto`

The database enforces uniqueness for the `(donor_id, need_id)` pair so that the same donor and community need cannot have duplicate match records.

Confirmed and rejected matches are treated as final coordinator decisions by the matching application. Recalculation does not overwrite the score or score breakdown associated with those decisions.

---

# Table: giving_history

Stores donation and finance-import records associated with donors and, when known, community needs and matches.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| gift_id | UUID | Yes | Primary Key | Unique identifier for each donation record. |
| donor_id | UUID | Yes | Foreign Key to donors.donor_id | Donor associated with the gift. |
| need_id | UUID | No | Nullable, Foreign Key to community_needs.need_id | Community need associated with the gift when known. |
| match_id | UUID | No | Nullable, Foreign Key to matches.match_id | Match associated with the gift when known. |
| amount | NUMERIC(12,2) | Yes | NOT NULL | Monetary amount of the donation. |
| in_kind_desc | VARCHAR(255) | No | Nullable | Description of a non-cash or in-kind donation. |
| channel | VARCHAR(50) | Yes | NOT NULL, CHECK Sendwave/Wave/other | Payment or donation channel. |
| transaction_ref | VARCHAR(100) | No | Nullable | Optional source transaction reference. |
| impact_note | TEXT | No | Nullable | Optional note describing the impact of the gift. |
| gift_date | TIMESTAMP | Yes | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the gift was made. |
| created_at | TIMESTAMP | Yes | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the record was created. |
| source_fingerprint | VARCHAR | No | Nullable, UNIQUE | Deterministic identifier used to prevent duplicate source transactions during imports. |

Allowed `channel` values:

* `Sendwave`
* `Wave`
* `other`

`need_id` and `match_id` are intentionally nullable because historical finance records may be imported before a reliable need or match relationship is known.

---

# Table: matching_runs

Stores metadata and processing statistics for each matching-engine execution.

| Field Name | Data Type | Required | Constraints | Description |
| --- | --- | --- | --- | --- |
| run_id | UUID | Yes | Primary Key | Unique identifier for the matching run. |
| started_at | TIMESTAMP | Yes | NOT NULL | Time the matching run started. |
| finished_at | TIMESTAMP | No | Nullable | Time the matching run completed or failed. |
| status | VARCHAR | Yes | NOT NULL | Current execution status of the matching run. |
| donors_scanned | INTEGER | Yes | NOT NULL, default 0 | Number of donors evaluated. |
| open_needs_scanned | INTEGER | Yes | NOT NULL, default 0 | Number of open community needs evaluated. |
| giving_history_records | INTEGER | Yes | NOT NULL, default 0 | Number of giving-history records available to the run. |
| total_combinations | INTEGER | Yes | NOT NULL, default 0 | Number of donor-need combinations evaluated. |
| qualified_matches | INTEGER | Yes | NOT NULL, default 0 | Number of combinations meeting the matching threshold. |
| inserted_matches | INTEGER | Yes | NOT NULL, default 0 | Number of new match records inserted. |
| updated_matches | INTEGER | Yes | NOT NULL, default 0 | Number of existing match records updated. |
| not_qualified_matches | INTEGER | Yes | NOT NULL, default 0 | Number of existing matches marked as not qualified where applicable. |
| skipped_matches | INTEGER | Yes | NOT NULL, default 0 | Number of combinations skipped by the matching process. |
| errors | INTEGER | Yes | NOT NULL, default 0 | Number of errors recorded during the run. |
| error_message | TEXT | No | Nullable | Error details recorded when a matching run fails. |

Typical run statuses include `running`, `completed`, and `failed`.

The matching engine uses a PostgreSQL advisory lock while a run is active to prevent two Streamlit sessions from running the matching process concurrently.

---

## Database Constraints and Safety Rules

The current schema and application logic include several protections:

* Donor email addresses are unique.
* Coordinator email addresses are unique.
* Category codes are unique.
* Community need urgency is constrained to values from 1 through 5.
* Community need workflow status is constrained to supported values.
* Each `(donor_id, need_id)` match pair is unique.
* `giving_history.source_fingerprint` provides database-level duplicate protection for imported finance transactions.
* Giving-history need and match relationships may be null when the source transaction has not yet been mapped.
* Final coordinator match decisions are protected from score/breakdown replacement by later matching runs.
* Matching runs use a database advisory lock to prevent concurrent matching-engine execution.

---

## Indexes

The database includes indexes to support common matching and workflow queries.

| Index Name | Table | Fields | Purpose |
| --- | --- | --- | --- |
| ix_community_needs_region_category_urgency_status | community_needs | region_id, category_id, urgency, status | Supports filtering needs by geography, category, urgency, and workflow status. |
| ix_matches_donor_need_status | matches | donor_id, need_id, status | Supports donor-to-need lookup and filtering by match status. |
| ix_giving_history_donor_need | giving_history | donor_id, need_id | Supports donor giving-history and need-level donation lookup. |

---

## Migration State

The current documented schema corresponds to Alembic revision:

`6185a5977580`

This revision is the current migration head at the time of this documentation update.

---

## Summary

This Data Dictionary documents the current core DVMP database schema, including donor and community-need data, matching, giving-history linkage, finance-import duplicate protection, and matching-run observability.

It should be updated whenever future migrations add, remove, or modify database tables, fields, constraints, indexes, or relationships.