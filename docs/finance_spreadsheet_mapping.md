# Finance Spreadsheet Mapping

## Overview

The finance spreadsheet contains historical transfer records for Gambia Garden. The file includes transfer dates, USD amounts, transfer fees, GMD amounts, sending method, and recipient details.

The spreadsheet also includes a summary total:

- Total Amount Sent (USD): 6424.09
- Total Amount Sent (GMD): 446519.22

The actual transfer records begin after the summary section.

---

## Spreadsheet Columns

| Spreadsheet Column | Meaning |
|--------------------|---------|
| Date mm/dd/yr | Date the transfer was made |
| Transfer Amount (USD) | Amount sent in USD before transfer fee |
| Transfer fee (USD) | Fee charged for the transfer |
| Transfer Total (USD) | Total USD charged including fee |
| Transfer Amount (GMD) | Amount converted to Gambian Dalasi |
| Total to reciever | Amount received by the recipient |
| Sending Details | Payment method/card details |
| Receiving Details | Recipient name and country |

---

## Proposed Database Mapping

| Spreadsheet Column | Database Table | Database Field | Notes |
|--------------------|----------------|----------------|-------|
| Date mm/dd/yr | giving_history | donation_date | Transfer date |
| Transfer Amount (USD) | giving_history | amount | Main donation amount |
| Transfer fee (USD) | giving_history | notes | Store as reference note |
| Transfer Total (USD) | giving_history | notes | Store as reference note |
| Transfer Amount (GMD) | giving_history | notes | Store as converted amount reference |
| Total to reciever | giving_history | notes | Store as amount received |
| Sending Details | giving_history | notes | Store payment method details |
| Receiving Details | giving_history | notes | Store recipient information |

---

## Data Quality Notes

- Dates appear to follow MM/DD/YYYY format.
- Amount fields are numeric.
- Recipient details are stored as free text.
- The column name `Total to reciever` has a spelling issue and should be interpreted as `Total to receiver`.
- The spreadsheet does not include donor_id, need_id, match_id, category, or region fields.
- Because no match or need reference is included, historical transfers cannot be automatically linked to specific community needs yet.

---

## Import Notes

Gambia Garden has already been seeded as the donor in the donors table.

When importing this spreadsheet later, each row should be treated as a historical giving record connected to the Gambia Garden donor. Any missing match_id or need_id fields should remain null unless additional mapping information is provided later.