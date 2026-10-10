#!/usr/bin/env python3
"""Verify the packaged static production preview renders the Evidence PDF with its module worker."""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

BASE_URL = os.getenv("CAUSORA_PRODUCTION_PREVIEW_URL", "http://127.0.0.1:4173").rstrip("/")
CHROMIUM = os.getenv("CAUSORA_CHROMIUM", "/usr/bin/chromium")
EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


async def main() -> None:
    errors: list[str] = []
    worker_responses: list[dict[str, object]] = []
    screenshot = EVIDENCE_DIR / "day4-production-evidence-pdf-1440x900.png"
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            executable_path=CHROMIUM,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        page.on("pageerror", lambda error: errors.append(str(error)))

        def capture_worker(response):
            if urlsplit(response.url).path.endswith("/pdf.worker.min.mjs"):
                worker_responses.append({
                    "status": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "url": response.url,
                })

        page.on("response", capture_worker)
        home = await page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=45_000)
        assert home and home.status == 200, f"production preview did not return HTTP 200: {home.status if home else 'no response'}"
        await page.get_by_role("button", name=re.compile("Data Intake", re.I)).click()
        await page.get_by_role("button", name=re.compile("Open source quote", re.I)).click()
        await page.get_by_text("No bbox was supplied; the highlight was derived from an exact text match", exact=False).wait_for(timeout=45_000)
        canvas = page.locator("canvas[aria-label='PDF page 4']")
        await canvas.wait_for(state="visible", timeout=10_000)
        await page.wait_for_function("() => { const c = document.querySelector(\"canvas[aria-label='PDF page 4']\"); return !!c && c.width > 0 && c.height > 0; }", timeout=10_000)
        assert worker_responses, "Chromium did not request the PDF.js .mjs worker"
        assert all(item["status"] == 200 for item in worker_responses), f"PDF.js worker request failed: {worker_responses}"
        assert all(str(item["content_type"]).lower().startswith(("text/javascript", "application/javascript")) for item in worker_responses), f"PDF.js worker did not receive a JavaScript MIME type: {worker_responses}"
        assert await page.locator(".evidence-pdf-error").count() == 0, "Evidence PDF viewer displayed a load error"
        assert not errors, f"browser runtime errors: {errors}"
        await page.screenshot(path=str(screenshot), full_page=False, animations="disabled")
        result = {
            "preview": BASE_URL,
            "status": "passed",
            "evidence": "EV-014, source PDF page 4",
            "worker_responses": worker_responses,
            "pdf_canvas_rendered": True,
            "exact_quote_highlight": True,
            "browser_errors": errors,
            "screenshot": str(screenshot),
        }
        await browser.close()
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
