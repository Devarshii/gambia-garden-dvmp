# Finance Spreadsheet Mapping

## Overview

The finance spreadsheet contains historical transfer records used to populate the `giving_history` table.

The raw finance spreadsheet is not stored in the public repository. This document intentionally describes only the fields required for the import process and does not include historical transfer totals, card details, recipient details, or other sensitive source information.

---

## Import Mapping

| Source Data | Database Table | Database Field | Notes |
| --- | --- | --- | --- |
| Transfer date | giving_history | gift_date | Date associated with the historical gift. |
| Transfer amount | giving_history | amount | Monetary amount used for the giving-history record. |
| Transfer channel | giving_history | channel | Normalized to a supported channel value. |
| Transaction reference | giving_history | transaction_ref | Optional non-sensitive transaction reference when available. |
| Donor | giving_history | donor_id | Resolved to the appropriate donor record during import. |
| Community need mapping | giving_history | need_id | Nullable when no reliable need mapping is available. |
| Match mapping | giving_history | match_id | Nullable when no match relationship is available. |
| Source transaction identity | giving_history | source_fingerprint | Deterministic fingerprint used to prevent duplicate imports. |

---

## Supported Channel Values

The importer normalizes supported transfer channels to:

- `Sendwave`
- `Wave`
- `other`

Unsupported or unrecognized source values should be handled according to the ETL validation rules rather than inserted directly.

---

## Need and Match Linkage

Historical finance records do not always contain a direct `need_id` or `match_id`.

For this reason:

- `giving_history.need_id` is nullable.
- `giving_history.match_id` is nullable.
- A separate local mapping file may be used to associate a source transaction with a known community need.
- Once a reliable need relationship is available, the imported giving-history record can contribute to need-level historical matching calculations.

The local mapping file is not intended to be committed to the public repository.

---

## Duplicate Prevention

Each imported source transaction is assigned a deterministic `source_fingerprint`.

The database enforces uniqueness for this fingerprint. The importer uses conflict-safe insertion so that rerunning an import, including overlapping import attempts, does not create duplicate records for the same source transaction.

---

## Data Quality and Privacy

The finance import should follow these rules:

- Validate transfer dates before insertion.
- Validate monetary amounts before insertion.
- Normalize supported channel values.
- Do not assume a community-need relationship when one cannot be established reliably.
- Leave `need_id` and `match_id` null when a reliable relationship is unavailable.
- Do not commit raw finance spreadsheets to the repository.
- Do not document or expose card/payment credentials or unnecessary recipient details.
- Do not include historical aggregate transfer totals in public documentation.
- Keep local transaction-to-need mapping data outside version control when it contains source-specific information.

---

## Import Behavior

Historical transfers are imported as `giving_history` records associated with the appropriate donor.

When an explicit transaction-to-need mapping is available, the importer can populate `need_id`. Otherwise, the relationship remains null until reliable mapping information is available.

`source_fingerprint` provides database-level idempotency so that the same source transaction is not inserted repeatedly.

Rejected or invalid source rows should be handled through the ETL validation/rejection process rather than silently inserted.

---

## Security Note

This document describes the import structure without reproducing sensitive finance information.

Raw transfer files, recipient-specific details, payment/card information, and source-specific mapping data should remain outside the public repository and should only be handled in appropriately secured environments.