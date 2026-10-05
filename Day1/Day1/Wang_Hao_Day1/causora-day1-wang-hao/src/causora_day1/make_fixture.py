"""Generate the self-contained synthetic PDF used in the Day 1 evidence tests."""
from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

CLAUSE_LINES = [
    "If written notice is not received at least 60 days before renewal,",
    "the agreement automatically renews for 24 months at a 14% higher unit price.",
    "A minimum purchase commitment equal to 60% of forecast demand applies.",
    "Early exit during the renewed term incurs a fixed termination fee of $25,000.",
]


def _font() -> str:
    # Font assets remain OS-provided; no external font file is redistributed.
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for font in candidates:
        if Path(font).exists():
            pdfmetrics.registerFont(TTFont("CausoraText", font))
            return "CausoraText"
    return "Helvetica"


def create_pdf(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=letter, pageCompression=1, invariant=1)
    c.setTitle("Supplier A Renewal Addendum - Synthetic Demo")
    c.setAuthor("Causora synthetic demo team")
    w, h = letter
    font = _font()
    c.setFillColor(colors.HexColor("#17324C"))
    c.rect(0, h - 18, w, 18, fill=1, stroke=0)
    c.setFont(font, 17)
    c.drawString(50, h - 75, "SUPPLIER A | RENEWAL ADDENDUM")
    c.setFillColor(colors.HexColor("#526575"))
    c.setFont(font, 9)
    c.drawString(50, h - 97, "CAUSORA DEMO DATA  /  SYNTHETIC DOCUMENT  /  NOT A REAL CONTRACT")
    c.setStrokeColor(colors.HexColor("#D2DCE4"))
    c.line(50, h - 116, w - 50, h - 116)
    c.setFillColor(colors.HexColor("#17324C"))
    c.setFont(font, 11)
    c.drawString(50, h - 151, "1. Renewal, pricing and purchase commitment")
    c.setFillColor(colors.black)
    c.setFont(font, 9.7)
    y = h - 178
    for line in CLAUSE_LINES:
        assert pdfmetrics.stringWidth(line, font, 9.7) < w - 100, line
        c.drawString(50, y, line)
        y -= 21
    c.setFillColor(colors.HexColor("#526575"))
    c.setFont(font, 9)
    c.drawString(50, h - 312, "Supplier A and the customer agree to the illustrative terms stated above.")
    c.drawString(50, h - 334, "The purpose of this file is traceable extraction and negative-case testing.")
    c.setStrokeColor(colors.HexColor("#D2DCE4"))
    c.line(50, 85, w - 50, 85)
    c.setFont(font, 8)
    c.drawString(50, 65, "Synthetic fixture v1  |  No commercial or legal effect")
    c.drawRightString(w - 50, 65, "Page 1 / 1")
    c.save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    create_pdf(parser.parse_args().output)
