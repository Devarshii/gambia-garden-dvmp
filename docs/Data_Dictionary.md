# Data Dictionary

## Project: Gambia Garden DVMP

This document defines the initial database tables, fields, data types, and relationships for the Gambia Garden Donor-Village Matching Platform.

---

## Core Tables

### donors

Stores donor profile and preference information.

| Field | Type | Description |
|---|---|---|
| donor_id | UUID / Primary Key | Unique identifier for each donor |
| first_name | VARCHAR | Donor first name |
| last_name | VARCHAR | Donor last name |
| email | VARCHAR | Donor email address |
| phone | VARCHAR | Donor phone number |
| preferred_regions | TEXT[] | Regions preferred by the donor |
| preferred_causes | TEXT[] | Causes preferred by the donor |
| total_given | DECIMAL | Total amount donated by the donor |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

---

### community_needs

Stores community need requests.

| Field | Type | Description |
|---|---|---|
| need_id | UUID / Primary Key | Unique identifier for each community need |
| title | VARCHAR | Title of the need |
| description | TEXT | Detailed description of the need |
| region_id | UUID / Foreign Key | Related region |
| category_id | UUID / Foreign Key | Related category |
| coordinator_id | UUID / Foreign Key | Assigned coordinator |
| priority_level | VARCHAR | Priority level of the need |
| estimated_amount | DECIMAL | Estimated funding amount needed |
| status | VARCHAR | Current need status |
| created_at | TIMESTAMP | Record creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

---

### matches

Stores donor-to-need match records.

| Field | Type | Description |
|---|---|---|
| match_id | UUID / Primary Key | Unique identifier for each match |
| donor_id | UUID / Foreign Key | Related donor |
| need_id | UUID / Foreign Key | Related community need |
| match_score | DECIMAL | Calculated match score |
| match_status | VARCHAR | Current match status |
| matched_at | TIMESTAMP | Match creation timestamp |
| confirmed_at | TIMESTAMP | Match confirmation timestamp |

---

### giving_history

Stores donation transaction history.

| Field | Type | Description |
|---|---|---|
| giving_id | UUID / Primary Key | Unique identifier for each giving record |
| donor_id | UUID / Foreign Key | Related donor |
| need_id | UUID / Foreign Key | Related community need |
| match_id | UUID / Foreign Key | Related match |
| amount | DECIMAL | Donation amount |
| donation_date | DATE | Date of donation |
| payment_method | VARCHAR | Donation payment method |
| notes | TEXT | Additional donation notes |
| created_at | TIMESTAMP | Record creation timestamp |

---

## Supporting Tables

### coordinators

Stores coordinator information.

| Field | Type | Description |
|---|---|---|
| coordinator_id | UUID / Primary Key | Unique identifier for each coordinator |
| first_name | VARCHAR | Coordinator first name |
| last_name | VARCHAR | Coordinator last name |
| email | VARCHAR | Coordinator email |
| phone | VARCHAR | Coordinator phone number |
| region_id | UUID / Foreign Key | Region assigned to coordinator |
| created_at | TIMESTAMP | Record creation timestamp |

---

### categories

Stores need/donation categories.

| Field | Type | Description |
|---|---|---|
| category_id | UUID / Primary Key | Unique identifier for each category |
| category_name | VARCHAR | Name of category |
| description | TEXT | Category description |

---

### regions

Stores geographic regions.

| Field | Type | Description |
|---|---|---|
| region_id | UUID / Primary Key | Unique identifier for each region |
| region_name | VARCHAR | Name of region |
| country | VARCHAR | Country name |
| description | TEXT | Region description |

---

## Key Relationships

- donors can have many matches.
- community_needs can have many matches.
- matches can connect one donor to one community need.
- donors can have many giving_history records.
- community_needs can have many giving_history records.
- matches can have related giving_history records.
- community_needs belongs to one category.
- community_needs belongs to one region.
- community_needs is managed by one coordinator.
- coordinators can be assigned to one region.