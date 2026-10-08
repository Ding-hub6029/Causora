"""Create the synthetic Day 1 input files. No real supplier, transaction or notice is represented.

Optional regeneration (the generated files are already committed and packaged):
    python3 -m pip install reportlab openpyxl
    python3 scripts/generate-demo-fixtures.py

The five evidence quotes are full sentences on PDF page 4; they can be checked with
`pdftotext -f 4 -l 4 -layout public/demo/supplier_a_agreement.pdf -`.
"""

from __future__ import annotations

import csv
import random
import shutil
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak, Spacer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "public" / "demo"
OUT.mkdir(parents=True, exist_ok=True)
RNG = random.Random(1042026)
shutil.copyfile(ROOT / "demo_data" / "supplier_correspondence_log.csv", OUT / "supplier_correspondence_log.csv")

with (OUT / "historical_demand.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["week_start", "units_demanded", "provenance"])
    start = date(2024, 10, 7)
    for week in range(104):
        value = max(0, round(250 + RNG.uniform(-36, 36) + 22 * (week % 13 == 0)))
        writer.writerow([(start + timedelta(weeks=week)).isoformat(), value, "synthetic_day1_fixture"])

with (OUT / "opening_inventory.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle, lineterminator="\n")
    writer.writerow(["as_of_date", "sku", "units_on_hand", "provenance"])
    writer.writerow(["2026-10-04", "DEMO-SKU-A", 1840, "synthetic_day1_fixture"])

workbook = Workbook()
sheet = workbook.active
sheet.title = "Synthetic deliveries"
sheet.append(["order_id", "supplier", "order_date", "arrival_date", "units", "base_price_usd", "provenance"])
for index in range(48):
    supplier = "A" if index % 4 else "B"
    ordered = date(2025, 10, 5) + timedelta(days=index * 7)
    lead = RNG.randint(12, 21) if supplier == "A" else RNG.randint(10, 19)
    sheet.append([f"PO-{index+1:03}", supplier, ordered.isoformat(), (ordered + timedelta(days=lead)).isoformat(), RNG.randint(100, 230), 12.0 if supplier == "A" else 12.6, "synthetic_day1_fixture"])
workbook.save(OUT / "supplier_delivery_history.xlsx")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="FixtureTitle", parent=styles["Title"], fontSize=20, leading=25, textColor=colors.HexColor("#153047"), spaceAfter=18))
styles.add(ParagraphStyle(name="FixtureHead", parent=styles["Heading2"], fontSize=14, leading=18, spaceBefore=14, spaceAfter=9, textColor=colors.HexColor("#153047")))
styles.add(ParagraphStyle(name="FixtureBody", parent=styles["BodyText"], fontSize=11, leading=18, spaceAfter=10, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="FixtureSmall", parent=styles["BodyText"], fontSize=9, leading=15, textColor=colors.HexColor("#536978")))

pages = [
    ("Supplier A Agreement — Synthetic Demo", [
        "THIS DOCUMENT IS SYNTHETIC DEMO DATA. It is not signed, enforceable or associated with any real supplier.",
        "The fictional supplier and buyer use this sample solely to test quote matching, source-page links and contract-constrained decisions in Causora.",
        "Version: demo-2026.10.04-r2. A separate synthetic notice register supplies the notice-sent assumption; this PDF alone cannot prove whether a notice was sent."
    ]),
    ("Parties and scope", [
        "Supplier A and Demo Buyer discuss a hypothetical 24-month supply relationship for DEMO-SKU-A. Names, amounts, dates and operational figures are fictional.",
        "This sample is intentionally machine-readable. It does not include signatures, real counterparties, or personal information."
    ]),
    ("Base pricing", [
        "The synthetic base unit price for Supplier A is $12.00 per unit, before any renewal uplift. Supplier B is shown in separate mock delivery history at a base price of $12.60 per unit.",
        "The Causora demonstration reports Supplier A purchase cost at the base price and the renewal uplift separately, exactly once, in the renewal premium component."
    ]),
    ("Renewal and minimum purchase — evidence page", [
        "If written notice is not received at least 60 days before renewal, the agreement automatically renews.",
        "The agreement automatically renews for 24 months at a 14% higher unit price.",
        "The renewed term has a minimum purchase commitment equal to 60% of forecast demand.",
        "Early exit during the renewed term incurs a fixed termination fee of $25,000.",
        "For the synthetic scenario only, the renewal-cycle forecast is fixed at 26,000 units for the coming term. The mock notice register supplies the explicit assumption that no timely written notice was recorded."
    ]),
    ("Operational interpretation", [
        "Scenario demand can fall after the forecast used for the minimum commitment was fixed. In the Day 1 stress preset it falls to 22,100 units; the contractual floor of 15,600 units from Supplier A remains unchanged in the demo.",
        "This example is an interpretive assumption for a synthetic clause, not a legal determination. Real contract implementation requires counsel and source verification."
    ]),
    ("Reproducibility notes", [
        "The five evidence records EV-014, EV-019, EV-021, EV-024 and EV-027 all point to page 4. EV-019 and EV-021 intentionally share the same source sentence because two distinct fields are extracted from it.",
        "For a live deployment, replace this document with an authorised, machine-readable agreement; verify every quote and, where possible, attach a PDF location rectangle."
    ])
]

def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#c3d3dc"))
    canvas.line(48, 53, letter[0] - 48, 53)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#536978"))
    canvas.drawString(48, 40, "SYNTHETIC / NOT A REAL CONTRACT")
    canvas.drawRightString(letter[0] - 48, 40, f"Page {doc.page} / 6")
    canvas.restoreState()

story = []
for index, (heading, paragraphs) in enumerate(pages):
    if index:
        story.append(PageBreak())
    story.append(Spacer(1, 30))
    story.append(Paragraph(heading, styles["FixtureTitle"]))
    story.append(Paragraph("CAUSORA · SYNTHETIC SOURCE FILE · DO NOT USE FOR PROCUREMENT", styles["FixtureSmall"]))
    story.append(Spacer(1, 16))
    for paragraph in paragraphs:
        story.append(Paragraph(paragraph, styles["FixtureBody"]))

SimpleDocTemplate(str(OUT / "supplier_a_agreement.pdf"), pagesize=letter, rightMargin=48, leftMargin=48, topMargin=55, bottomMargin=70,
                  title="Synthetic Supplier A Agreement — Causora Day 1", author="Causora Demo Team").build(story, onFirstPage=footer, onLaterPages=footer)
print("Generated four synthetic source files in public/demo/ (CSV, XLSX, CSV, PDF).")
