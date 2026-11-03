#!/usr/bin/env python3
"""Invoice intake pipeline: PDF in, validated spreadsheet rows out.

Reads every PDF in ./inbox, extracts the header fields, checks the arithmetic,
flags duplicates and outliers, and writes two files: invoices.csv for the rows
that are safe to post to the ledger, exceptions.csv for the ones a human must
look at. No cloud services, no credentials, runs in one pass.

Usage: python3 extract.py [indir] [outdir]
"""
import csv, json, re, sys, time
from collections import Counter
from datetime import datetime
from pathlib import Path

import pdfplumber

MONEY = r"([\u00a3$\u20ac])\s*([\d,]+\.\d{2})"
CUR = {"\u00a3": "GBP", "$": "USD", "\u20ac": "EUR"}
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%b %d, %Y")
OUTLIER_USD = 5000.0
FX = {"GBP": 1.27, "EUR": 1.08, "USD": 1.0}


def parse_date(s):
    s = (s or "").strip()
    for f in DATE_FORMATS:
        try:
            return datetime.strptime(s, f).date().isoformat()
        except ValueError:
            continue
    return None


def money(text, pattern):
    m = re.search(pattern, text)
    if not m:
        return None, None
    return float(m.group(2).replace(",", "")), CUR.get(m.group(1))


def parse(path):
    with pdfplumber.open(str(path)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    if len(text.strip()) < 40:
        return {"file": path.name, "error": "no text layer, needs OCR"}

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    num = re.search(r"Invoice no:\s*([A-Za-z0-9\-/]+)", text)
    issued = re.search(r"Issued:\s*([^\n]+)", text)
    due = re.search(r"Due:\s*([^\n]+)", text)
    sub, cur = money(text, r"Subtotal\s*" + MONEY)
    tax, _ = money(text, r"VAT 20%\s*" + MONEY)
    total, cur2 = money(text, r"Total due\s*" + MONEY)

    rec = {
        "file": path.name,
        "vendor": lines[0] if lines else None,
        "invoice_no": num.group(1) if num else None,
        "issued": parse_date(issued.group(1)) if issued else None,
        "due": parse_date(due.group(1)) if due else None,
        "currency": cur2 or cur,
        "subtotal": sub,
        "tax": tax,
        "total": total,
    }
    rec["total_usd"] = round(total * FX.get(rec["currency"], 1.0), 2) if total else None
    return rec


def validate(recs):
    counts = Counter(r["invoice_no"].upper() for r in recs if r.get("invoice_no"))
    for r in recs:
        flags = []
        if r.get("error"):
            r["flags"] = r["error"]
            continue
        if all(r[k] is not None for k in ("subtotal", "tax", "total")):
            if abs((r["subtotal"] + r["tax"]) - r["total"]) > 0.02:
                flags.append("arithmetic mismatch")
        else:
            flags.append("amount not parsed")
        if not r.get("invoice_no"):
            flags.append("missing invoice no")
        elif counts[r["invoice_no"].upper()] > 1:
            flags.append("duplicate invoice number")
        if not r.get("issued"):
            flags.append("missing issue date")
        if not r.get("due"):
            flags.append("missing due date")
        elif r.get("issued") and r["due"] < r["issued"]:
            flags.append("due before issue")
        if (r.get("total_usd") or 0) > OUTLIER_USD:
            flags.append("outlier amount, verify")
        r["flags"] = "; ".join(flags)
    return recs


def main():
    indir = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "inbox")
    outdir = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).parent / "out")
    outdir.mkdir(exist_ok=True)
    files = sorted(indir.glob("*.pdf"))
    t0 = time.time()
    recs = validate([parse(f) for f in files])
    elapsed = time.time() - t0

    clean = [r for r in recs if not r["flags"]]
    dirty = [r for r in recs if r["flags"]]
    cols = ["vendor", "invoice_no", "issued", "due", "currency", "subtotal", "tax", "total",
            "total_usd", "file", "flags"]
    with open(outdir / "invoices.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in sorted(clean, key=lambda x: (x["issued"] or "", x["invoice_no"] or "")):
            w.writerow(r)
    with open(outdir / "exceptions.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in dirty:
            w.writerow(r)

    summary = {
        "pdfs": len(files),
        "clean": len(clean),
        "exceptions": len(dirty),
        "exception_types": dict(Counter(t.strip() for r in dirty for t in r["flags"].split(";"))),
        "total_value_usd": round(sum(r.get("total_usd") or 0 for r in clean), 2),
        "seconds": round(elapsed, 2),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))
    for r in dirty:
        print(f"  EXC {r['file']:<22} {str(r.get('invoice_no')):<16} {r['flags']}")


if __name__ == "__main__":
    main()
