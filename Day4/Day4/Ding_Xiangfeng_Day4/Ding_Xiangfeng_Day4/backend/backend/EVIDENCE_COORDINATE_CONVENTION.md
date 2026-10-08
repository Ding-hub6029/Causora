# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# Evidence locator coordinate convention

`GET /api/evidence/{id}` returns `locatorBbox` as `[x0, y0, x1, y1]` in **unrotated PDF user-space points with a bottom-left origin**.

## Conversion performed by the backend

1. PyMuPDF opens the physical source PDF and calls `page.search_for(quote)`.
2. PyMuPDF search rectangles have a page-local **top-left** origin. Multiple rectangles are unioned so a multi-line exact quote remains one highlight region.
3. With `H = page.mediabox.height`, the backend returns:

```text
[x0, H - y1, x1, H - y0]
```

4. The backend rejects an absent quote, invalid page, inverted rectangle, or a rectangle outside the media box. It never returns an unverified legacy locator.

## Frontend rule

Ding's `resolveEvidenceLocator` must call `PDFPageViewport.convertToViewportPoint` on both opposite corners. PDF.js then applies the active zoom and page rotation. The frontend must **not** invert `y`, scale the result, or assume a browser-pixel coordinate system a second time.

This convention was selected because PDF.js consumes bottom-left PDF user-space points while PyMuPDF emits top-left page coordinates. The conversion keeps the API independent of the user's viewport dimensions and zoom level.

## Scope

The source file, page, quote, and `quoteMatched: true` are revalidated against the physical PDF before a simulation is accepted as a Boardroom input. The evidence endpoint calculates the locator from the retained current run; it does not trust a stale bbox from a JSON fixture.
