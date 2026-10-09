"""Source-backed PDF quote rectangles for the public EvidenceRecord DTO.

PyMuPDF reports rectangles in a page-local coordinate system with a *top-left*
origin.  PDF.js ``PageViewport.convertToViewportPoint`` consumes PDF user-space
points with a *bottom-left* origin and applies the active page rotation/scale.
This module makes that conversion once at the server boundary so callers must
not mix coordinate systems.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence


class EvidenceLocatorError(ValueError):
    """A source quote cannot safely be expressed as a PDF.js locator."""


def _union(rectangles: Sequence[object]) -> tuple[float, float, float, float]:
    if not rectangles:
        raise EvidenceLocatorError("exact quote has no searchable rectangle")
    try:
        x0 = min(float(rect.x0) for rect in rectangles)
        y0 = min(float(rect.y0) for rect in rectangles)
        x1 = max(float(rect.x1) for rect in rectangles)
        y1 = max(float(rect.y1) for rect in rectangles)
    except (AttributeError, TypeError, ValueError) as exc:
        raise EvidenceLocatorError("PDF quote rectangle is invalid") from exc
    if not (x0 >= 0 and y0 >= 0 and x1 > x0 and y1 > y0):
        raise EvidenceLocatorError("PDF quote rectangle is inverted or outside the page")
    return x0, y0, x1, y1


def pdfjs_user_space_bbox(pdf_path: Path, page_one_based: int, quote: str) -> list[float]:
    """Return ``[x0, y0, x1, y1]`` in PDF.js PDF-user-space coordinates.

    The returned y coordinates use a bottom-left origin.  The frontend must call
    ``viewport.convertToViewportPoint`` for both opposing corners; it must not
    apply a second y-axis inversion, scale, or page-rotation transform.
    """
    if not isinstance(page_one_based, int) or isinstance(page_one_based, bool) or page_one_based < 1:
        raise EvidenceLocatorError("PDF page number is invalid")
    if not isinstance(quote, str) or not quote.strip():
        raise EvidenceLocatorError("evidence quote is invalid")
    try:
        import pymupdf
        document = pymupdf.open(pdf_path)
    except Exception as exc:
        raise EvidenceLocatorError("evidence source cannot be opened") from exc
    try:
        if page_one_based > document.page_count:
            raise EvidenceLocatorError("evidence page is outside the source document")
        page = document[page_one_based - 1]
        rectangles = page.search_for(quote)
        top_left_x0, top_left_y0, top_left_x1, top_left_y1 = _union(rectangles)
        # Search rectangles use PyMuPDF's top-left origin.  The media box is the
        # unrotated PDF user-space height that PDF.js receives before viewport
        # rotation/scale.  Convert the two diagonal corners, reversing y order.
        height = float(page.mediabox.height)
        if not height > 0 or top_left_y1 > height + 1e-6:
            raise EvidenceLocatorError("evidence rectangle exceeds the PDF media box")
        result = [top_left_x0, height - top_left_y1, top_left_x1, height - top_left_y0]
        if not (result[0] >= 0 and result[1] >= 0 and result[2] > result[0] and result[3] > result[1]):
            raise EvidenceLocatorError("converted PDF.js rectangle is invalid")
        return [round(value, 4) for value in result]
    except EvidenceLocatorError:
        raise
    except Exception as exc:
        raise EvidenceLocatorError("evidence quote cannot be located in source PDF") from exc
    finally:
        document.close()
