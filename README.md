# Invoice intake, a reference build

A small, complete automation: PDFs in, validated spreadsheet rows out.

Built to show the shape of work I do: fixed scope, five working days, no cloud
services, no credentials, everything runs on your own machine.

## What it does

`extract.py` reads every PDF in `inbox/`, pulls the header fields, reconciles the
arithmetic, and splits the batch:

- `out/invoices.csv`, rows that are safe to post to the ledger
- `out/exceptions.csv`, rows a human must look at, each with the reason

Checks included: line item totals against the stated total, duplicate invoice
numbers across suppliers, a USD threshold for outliers, and a missing-text-layer
detection so a scanned image is reported instead of silently dropped.

## Run it

```bash
python3 gen_invoices.py     # writes 13 supplier invoices into inbox/
python3 extract.py          # reads inbox/, writes out/
```

Requires `fpdf2` (generator only) and `pdfplumber`. No API keys.

## The sample batch

13 invoices across 5 suppliers, 3 currencies (GBP, EUR, USD), 3 date formats and
3 layout families, with four defects seeded on purpose:

| Defect | Where it surfaces |
| --- | --- |
| Line items do not sum to the stated total | exceptions.csv |
| Same invoice number used by two suppliers | exceptions.csv |
| Due date missing | exceptions.csv |
| Scan with no text layer | exceptions.csv |

Result on a 2 GB VPS: whole batch parsed and validated in 0.34 s, 8 rows clean,
5 held for review.

## Deliberate limits

- No database and no scheduler. It is a batch job, not a service.
- Currency conversion uses fixed rates, so converted totals are for comparison
  only, never for posting.
- Any supplier whose layout departs from the three families here needs a parser
  added, which is the honest cost of doing this without a paid document API.
