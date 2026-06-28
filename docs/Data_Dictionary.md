# Gambia Garden DVMP - Data Dictionary

## Overview

This document describes the database tables and fields used in the Gambia Garden Donor-Village Matching Platform (DVMP).

It explains each table, column, data type, constraint, and plain-language purpose so future developers, fellows, and Gambia Garden staff can understand and extend the database.

---

## Design Notes

### total_given Design Note

The `total_given` value is not stored in the `donors` table.

Instead, total donor giving must be calculated from the `giving_history` table using:

```sql
SELECT donor_id, SUM(amount) AS total_given
FROM giving_history
GROUP BY donor_id;
```

This avoids duplicate stored data and ensures donation totals remain accurate.

### preferred_regions v1 Limitation Note

The `preferred_regions` field in the `donors` table is stored as a `TEXT[]` array rather than foreign key references to the `regions` table.

This is a known v1 simplification. In a future migration, this may be normalized using a donor-region relationship table when matching logic becomes more mature.

---

# Table: regions

Stores geographic regions used for matching community needs with donors and coordinators.

| Field Name  | Data Type    | Required | Constraints | Description                             |
| ----------- | ------------ | -------- | ----------- | --------------------------------------- |
| region_id   | UUID         | Yes      | Primary Key | Unique identifier for each region.      |
| region_code | VARCHAR(50)  | Yes      | NOT NULL    | Short code used to identify the region. |
| region_name | VARCHAR(100) | Yes      | NOT NULL    | Full name of the region.                |
| country     | VARCHAR(100) | Yes      | NOT NULL    | Country where the region is located.    |
| notes       | TEXT         | No       | Nullable    | Optional notes about the region.        |

---

# Table: categories

Stores need categories such as education, health, water, agriculture, or infrastructure.

| Field Name    | Data Type    | Required | Constraints            | Description                                         |
| ------------- | ------------ | -------- | ---------------------- | --------------------------------------------------- |
| category_id   | UUID         | Yes      | Primary Key            | Unique identifier for each category.                |
| category_code | VARCHAR(50)  | Yes      | NOT NULL, UNIQUE       | Short unique code for the category.                 |
| label         | VARCHAR(100) | Yes      | NOT NULL               | Human-readable category name.                       |
| description   | TEXT         | No       | Nullable               | Optional explanation of the category.               |
| is_active     | BOOLEAN      | Yes      | NOT NULL, default TRUE | Indicates whether the category is currently active. |

---

# Table: coordinators

Stores local coordinators who manage community needs in specific regions.

| Field Name | Data Type    | Required | Constraints                         | Description                                            |
| ---------- | ------------ | -------- | ----------------------------------- | ------------------------------------------------------ |
| coord_id   | UUID         | Yes      | Primary Key                         | Unique identifier for each coordinator.                |
| name       | VARCHAR(100) | Yes      | NOT NULL                            | Full name of the coordinator.                          |
| email      | VARCHAR(150) | Yes      | NOT NULL, UNIQUE                    | Coordinator email address.                             |
| phone      | VARCHAR(30)  | No       | Nullable                            | Optional phone number for the coordinator.             |
| region_id  | UUID         | Yes      | Foreign Key to regions.region_id    | Region assigned to the coordinator.                    |
| is_active  | BOOLEAN      | Yes      | NOT NULL, default TRUE              | Indicates whether the coordinator is currently active. |
| created_at | TIMESTAMP    | Yes      | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the coordinator record was created. |

---

# Table: donors

Stores donor profile information, donation interests, giving capacity, and matching preferences.

| Field Name        | Data Type     | Required | Constraints                         | Description                                                        |
| ----------------- | ------------- | -------- | ----------------------------------- | ------------------------------------------------------------------ |
| donor_id          | UUID          | Yes      | Primary Key                         | Unique identifier for each donor.                                  |
| name              | VARCHAR(150)  | Yes      | NOT NULL                            | Full name of the donor.                                            |
| email             | VARCHAR(150)  | Yes      | NOT NULL, UNIQUE                    | Donor email address.                                               |
| location          | VARCHAR(150)  | No       | Nullable                            | Donor's location.                                                  |
| interests         | TEXT[]        | No       | Nullable                            | List of donor interest areas.                                      |
| giving_capacity   | NUMERIC(12,2) | No       | Nullable                            | Estimated amount the donor may be able to give.                    |
| preferred_causes  | TEXT[]        | No       | Nullable                            | Causes the donor prefers to support.                               |
| preferred_regions | TEXT[]        | No       | Nullable                            | Regions the donor prefers to support. Stored as text values in v1. |
| created_at        | TIMESTAMP     | Yes      | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the donor record was created.                   |
| updated_at        | TIMESTAMP     | Yes      | NOT NULL, default CURRENT_TIMESTAMP | Date and time when the donor record was last updated.              |

---

# Table: community_needs

Stores needs submitted by communities, including region, category, urgency, status, cost, and coordinator ownership.

| Field Name     | Data Type     | Required | Constraints                                            | Description                                      |
| -------------- | ------------- | -------- | ------------------------------------------------------ | ------------------------------------------------ |
| need_id        | UUID          | Yes      | Primary Key                                            | Unique identifier for each community need.       |
| region_id      | UUID          | Yes      | Foreign Key to regions.region_id                       | Region where the need exists.                    |
| category_id    | UUID          | Yes      | Foreign Key to categories.category_id                  | Category of the need.                            |
| coord_id       | UUID          | Yes      | Foreign Key to coordinators.coord_id                   | Coordinator responsible for the need.            |
| village        | VARCHAR(150)  | Yes      | NOT NULL                                               | Village where the need is located.               |
| urgency        | INTEGER       | Yes      | NOT NULL, CHECK 1 to 5                                 | Urgency rating from 1 to 5.                      |
| status         | VARCHAR(50)   | Yes      | NOT NULL, default 'open', CHECK open/matched/fulfilled | Current workflow status of the need.             |
| description    | TEXT          | No       | Nullable                                               | Detailed explanation of the community need.      |
| photo_urls     | TEXT[]        | No       | Nullable                                               | Optional list of photo URLs related to the need. |
| estimated_cost | NUMERIC(12,2) | No       | Nullable                                               | Estimated cost required to fulfill the need.     |
| created_at     | TIMESTAMP     | Yes      | NOT NULL, default CURRENT_TIMESTAMP                    | Date and time when the need was created.         |
| resolved_at    | TIMESTAMP     | No       | Nullable                                               | Date and time when the need was resolved.        |

Allowed values:

* `urgency`: 1, 2, 3, 4, 5
* `status`: `open`, `matched`, `fulfilled`

---

# Table: matches

Stores donor-to-need match records created manually or automatically.

| Field Name        | Data Type    | Required | Constraints                            | Description                                          |
| ----------------- | ------------ | -------- | -------------------------------------- | ---------------------------------------------------- |
| match_id          | UUID         | Yes      | Primary Key                            | Unique identifier for each match.                    |
| donor_id          | UUID         | Yes      | Foreign Key to donors.donor_id         | Donor involved in the match.                         |
| need_id           | UUID         | Yes      | Foreign Key to community_needs.need_id | Community need involved in the match.                |
| match_date        | TIMESTAMP    | Yes      | NOT NULL, default CURRENT_TIMESTAMP    | Date and time when the match was created.            |
| match_type        | VARCHAR(50)  | Yes      | NOT NULL, CHECK manual/auto            | Indicates whether the match was manual or automatic. |
| match_score       | NUMERIC(5,2) | No       | Nullable                               | Optional score representing match quality.           |
| status            | VARCHAR(50)  | No       | Nullable                               | Current status of the match.                         |
| coordinator_notes | TEXT         | No       | Nullable                               | Optional notes from the coordinator.                 |
| confirmed_at      | TIMESTAMP    | No       | Nullable                               | Date and time when the match was confirmed.          |

Allowed values:

* `match_type`: `manual`, `auto`

---

# Table: giving_history

Stores actual donation records connected to donors, needs, and matches.

| Field Name      | Data Type     | Required | Constraints                            | Description                                         |
| --------------- | ------------- | -------- | -------------------------------------- | --------------------------------------------------- |
| gift_id         | UUID          | Yes      | Primary Key                            | Unique identifier for each donation record.         |
| donor_id        | UUID          | Yes      | Foreign Key to donors.donor_id         | Donor who gave the gift.                            |
| need_id         | UUID          | Yes      | Foreign Key to community_needs.need_id | Community need supported by the gift.               |
| match_id        | UUID          | Yes      | Foreign Key to matches.match_id        | Match associated with the gift.                     |
| amount          | NUMERIC(12,2) | Yes      | NOT NULL                               | Monetary amount of the donation.                    |
| in_kind_desc    | VARCHAR(255)  | No       | Nullable                               | Description of any non-cash or in-kind donation.    |
| channel         | VARCHAR(50)   | Yes      | NOT NULL, CHECK Sendwave/Wave/other    | Payment or donation channel used.                   |
| transaction_ref | VARCHAR(100)  | No       | Nullable                               | Optional transaction reference number.              |
| impact_note     | TEXT          | No       | Nullable                               | Optional note describing the impact of the gift.    |
| gift_date       | TIMESTAMP     | Yes      | NOT NULL, default CURRENT_TIMESTAMP    | Date and time when the gift was made.               |
| created_at      | TIMESTAMP     | Yes      | NOT NULL, default CURRENT_TIMESTAMP    | Date and time when the donation record was created. |

Allowed values:

* `channel`: `Sendwave`, `Wave`, `other`

---

## Indexes

The database includes the following indexes to improve query performance:

| Index Name                                        | Table           | Fields                                  | Purpose                                                                        |
| ------------------------------------------------- | --------------- | --------------------------------------- | ------------------------------------------------------------------------------ |
| ix_community_needs_region_category_urgency_status | community_needs | region_id, category_id, urgency, status | Supports filtering needs by geography, category, urgency, and workflow status. |
| ix_matches_donor_need_status                      | matches         | donor_id, need_id, status               | Supports donor-to-need match lookup and filtering by match status.             |
| ix_giving_history_donor_need                      | giving_history  | donor_id, need_id                       | Supports donor giving history and need-level donation tracking.                |

---

## Summary

This Data Dictionary v1 documents all core DVMP database tables and fields.

It should be updated whenever future migrations add, remove, or change tables, fields, constraints, or relationships.
