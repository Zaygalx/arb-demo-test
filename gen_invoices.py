#!/usr/bin/env python3
"""Generate a realistic mixed batch of supplier invoice PDFs for the demo.

Three layout families, three date formats, three currencies, and four seeded
defects so the pipeline has something to catch: an arithmetic mismatch, a
duplicate invoice number, a missing due date, and one image-only invoice with
no text layer.
"""
import random
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)
from pathlib import Path
from fpdf import FPDF

OUT = Path(__file__).parent / "inbox"
OUT.mkdir(exist_ok=True)
random.seed(7)

VENDORS = [
    ("Northwind Supply Co.", "12 Harbour Rd, Bristol BS1 4RN", "GBP", "£"),
    ("Cedar & Vale Ltd", "88 King St, Manchester M2 4WQ", "GBP", "£"),
    ("Bluepeak Logistics", "4400 W Madison St, Chicago IL", "USD", "$"),
    ("Marchetti Forniture", "Via Roma 44, Milano", "EUR", "€"),
    ("Halcyon Print House", "9 Quay Parade, Dublin 2", "EUR", "€"),
]
ITEMS = [
    ("A4 copier paper, box of 5", 24.50, 4),
    ("Toner cartridge HP 26A", 78.00, 2),
    ("Pallet wrap, 500mm roll", 12.75, 8),
    ("Courier, next day pallet", 45.00, 1),
    ("Vinyl banner 2m x 1m", 96.00, 1),
    ("Storage rack, 5 shelf", 132.40, 2),
]
DATE_FMT = ["iso", "eu", "us_text"]


def fmt_date(fmt, d, m, y):
    if fmt == "iso":
        return f"{y}-{m:02d}-{d:02d}"
    if fmt == "eu":
        return f"{d:02d}/{m:02d}/{y}"
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{months[m]} {d}, {y}"


def make_pdf(path, vendor, addr, code, sym, number, issued, due, lines, total_override=None,
             due_missing=False):
    pdf = FPDF()
    pdf.add_page()
    pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    pdf.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    pdf.add_font("DejaVu", "I", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    pdf.set_font("DejaVu", "B", 18)
    pdf.cell(0, 12, vendor, ln=1)
    pdf.set_font("DejaVu", "", 9)
    pdf.cell(0, 5, addr, ln=1)
    pdf.ln(6)
    pdf.set_font("DejaVu", "B", 13)
    pdf.cell(0, 8, "INVOICE", ln=1)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(0, 5, f"Invoice no: {number}", ln=1)
    pdf.cell(0, 5, f"Issued: {issued}", ln=1)
    if not due_missing:
        pdf.cell(0, 5, f"Due: {due}", ln=1)
    pdf.ln(6)
    pdf.set_font("DejaVu", "B", 10)
    pdf.cell(95, 7, "Description", border="B")
    pdf.cell(25, 7, "Qty", border="B", align="R")
    pdf.cell(30, 7, "Unit", border="B", align="R")
    pdf.cell(35, 7, "Amount", border="B", align="R", ln=1)
    pdf.set_font("DejaVu", "", 10)
    subtotal = 0.0
    for desc, price, qty in lines:
        amt = price * qty
        subtotal += amt
        pdf.cell(95, 7, desc)
        pdf.cell(25, 7, str(qty), align="R")
        pdf.cell(30, 7, f"{sym}{price:,.2f}", align="R")
        pdf.cell(35, 7, f"{sym}{amt:,.2f}", align="R", ln=1)
    tax = round(subtotal * 0.20, 2)
    total = round(subtotal + tax, 2)
    shown_total = total_override if total_override is not None else total
    pdf.ln(3)
    pdf.set_font("DejaVu", "", 10)
    pdf.cell(150, 6, "Subtotal", align="R")
    pdf.cell(35, 6, f"{sym}{subtotal:,.2f}", align="R", ln=1)
    pdf.cell(150, 6, "VAT 20%", align="R")
    pdf.cell(35, 6, f"{sym}{tax:,.2f}", align="R", ln=1)
    pdf.set_font("DejaVu", "B", 11)
    pdf.cell(150, 7, "Total due", align="R")
    pdf.cell(35, 7, f"{sym}{shown_total:,.2f}", align="R", ln=1)
    pdf.set_font("DejaVu", "I", 8)
    pdf.ln(6)
    pdf.cell(0, 5, f"Payment terms: 30 days. Currency {code}. Thank you for your business.", ln=1)
    pdf.output(str(path))


def main():
    n = 1
    seeded = 0
    for i in range(12):
        vendor, addr, code, sym = VENDORS[i % len(VENDORS)]
        number = f"INV-2026-{1000 + n}"
        issued = fmt_date(DATE_FMT[i % 3], 3 + i, 8 + (i % 2), 2026)
        due = fmt_date(DATE_FMT[i % 3], 2 + i, 9 + (i % 2), 2026)
        lines = random.sample(ITEMS, random.choice([2, 3, 4]))
        override, missing = None, False
        if i == 4:  # arithmetic mismatch
            override = 9999.99
            seeded += 1
        if i == 7:  # duplicate number of invoice 3
            number = "INV-2026-1003"
            seeded += 1
        if i == 9:  # missing due date
            missing = True
            seeded += 1
        make_pdf(OUT / f"{number.lower()}-{i}.pdf", vendor, addr, code, sym, number,
                 issued, due, lines, total_override=override, due_missing=missing)
        n += 1

    # image-only invoice: a page with no text layer at all
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, "", ln=1)
    pdf.output(str(OUT / "scan-0000.pdf"))
    seeded += 1
    print(f"wrote {len(list(OUT.glob('*.pdf')))} pdfs to {OUT} ({seeded} seeded defects)")


if __name__ == "__main__":
    main()
