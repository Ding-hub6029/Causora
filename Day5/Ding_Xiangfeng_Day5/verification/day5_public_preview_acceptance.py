from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright


PREVIEW_URL = os.environ.get("CAUSORA_PREVIEW_URL", "").strip().rstrip("/")
if not PREVIEW_URL.startswith("https://"):
    raise SystemExit("CAUSORA_PREVIEW_URL must be an HTTPS public staging URL")

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "verification" / "g5-public-preview"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


async def main() -> None:
    results: dict[str, object] = {
        "preview_url": PREVIEW_URL,
        "fresh_context": True,
        "checks": {},
        "screenshots": [],
        "api_requests": [],
        "console_errors": [],
    }
    requests: list[str] = []
    console_errors: list[str] = []
    worker_responses: list[dict[str, str | None]] = []
    pdf_responses: list[dict[str, str | None]] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        await context.add_init_script("localStorage.clear(); sessionStorage.clear();")
        page = await context.new_page()
        page.on("request", lambda request: requests.append(request.url))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("pageerror", lambda error: console_errors.append(f"pageerror: {error}"))

        async def capture_response(response) -> None:
            path = urlparse(response.url).path
            metadata = {"url": response.url, "status": str(response.status), "content_type": await response.header_value("content-type")}
            if path.endswith("/pdf.worker.min.mjs"):
                worker_responses.append(metadata)
            if path.lower().endswith(".pdf"):
                pdf_responses.append(metadata)

        page.on("response", lambda response: asyncio.create_task(capture_response(response)))
        try:
            response = await page.goto(PREVIEW_URL, wait_until="networkidle", timeout=60_000)
            require(response is not None and response.status == 200, "Public staging did not return HTTP 200")
            await page.get_by_text("Public backend not configured", exact=True).wait_for(timeout=20_000)
            initial_storage = await page.evaluate("localStorage.length")
            results["initial_local_storage_entries"] = initial_storage
            require(initial_storage == 0, f"Browser context was not empty before use: localStorage={initial_storage}")
            require(await page.get_by_role("button", name=re.compile("Open Verified Golden Run", re.I)).count() == 1,
                    "The public backend-unavailable state did not offer the bundled Verified Golden Run")
            await page.screenshot(path=str(OUT_DIR / "day5-staging-cold-start-1440x1000.png"), full_page=True)
            results["screenshots"].append("day5-staging-cold-start-1440x1000.png")
            results["checks"]["public_https_and_static_only_state"] = "PASS"

            await page.get_by_role("button", name=re.compile("Open Verified Golden Run", re.I)).click()
            await page.get_by_label("Verified Golden provenance").wait_for(timeout=30_000)
            provenance = await page.get_by_label("Verified Golden provenance").inner_text()
            require("SITE-BUNDLED" in provenance and "automated G4 UI-test artifact" in provenance,
                    "Golden provenance did not identify the bundled source and automated-test-only choice")
            require("No backend call is made" in provenance, "Golden provenance did not declare read-only/no-backend behavior")
            results["checks"]["fresh_browser_verified_golden"] = "PASS"

            stages = page.locator(".stage-nav-item")
            require(await stages.count() == 5, "The five-stage workflow is not present on the public staging page")

            await stages.nth(2).click()
            await page.get_by_text("CACHED · VERIFIED GOLDEN · READ-ONLY", exact=True).wait_for(timeout=20_000)
            matrix_text = await page.locator("body").inner_text()
            require("LIVE API ·" not in matrix_text and "LIVE API RESPONSE VALIDATED" not in matrix_text,
                    "Matrix/proof narrative falsely presents cached run data as live")
            require("VERIFIED GOLDEN EVIDENCE · READ-ONLY" in matrix_text and "STORED POLICY INPUTS · READ-ONLY" in matrix_text,
                    "ProofEngine source/variable cards are not bound to the revalidated Golden evidence records")
            require("SAVED DEMO SOURCE · NOT LIVE" not in matrix_text and "SAVED DEMO CONTRACT · NOT LIVE" not in matrix_text,
                    "ProofEngine is mixing Day2 demo provenance into the Golden snapshot view")
            await page.screenshot(path=str(OUT_DIR / "day5-staging-matrix-1440x1000.png"), full_page=True)
            results["screenshots"].append("day5-staging-matrix-1440x1000.png")
            results["checks"]["cached_matrix_no_false_live"] = "PASS"

            await stages.nth(3).click()
            await page.get_by_text("CACHED · VERIFIED BOARDROOM", exact=True).wait_for(timeout=20_000)
            boardroom_text = await page.locator("body").inner_text()
            require("LIVE BOARDROOM · PRIMARY" not in boardroom_text and "LIVE · SAME-FAMILY REVIEW" not in boardroom_text,
                    "Cached Boardroom is falsely labelled as a live provider call")
            require("No AI provider is called in this replay" in boardroom_text,
                    "Boardroom replay does not explain the static snapshot boundary")
            results["checks"]["cached_boardroom_no_live_provider_claim"] = "PASS"

            await stages.nth(4).click()
            await page.get_by_text("CACHED VERIFIED REVIEW · READ-ONLY", exact=True).wait_for(timeout=20_000)
            brief_text = await page.locator("body").inner_text()
            require("automated G4 UI-test artifact" in brief_text,
                    "Stored Rejected choice is not explicitly scoped to the automated G4 UI test")
            require("No human business decision was recorded" in brief_text,
                    "Cached Rejected choice is being presented without an explicit human-decision boundary")
            require("HUMAN REJECTED" not in brief_text and "BY HUMAN REVIEWER" not in brief_text,
                    "Proof panel falsely labels the automated test choice as a human rejection")
            require(await page.get_by_role("button", name=re.compile("Record human approval|Record rejection", re.I)).count() == 0,
                    "Read-only Golden snapshot exposes a human approval/rejection action")
            results["checks"]["stored_choice_provenance_and_read_only"] = "PASS"

            evidence_button = page.get_by_role("button", name=re.compile("Open verified Evidence", re.I)).first
            await evidence_button.click()
            await page.get_by_role("dialog", name="Evidence detail").wait_for(timeout=20_000)
            viewer = page.locator(".evidence-pdf-viewer")
            await viewer.locator(".evidence-pdf-page.ready").wait_for(timeout=60_000)
            canvas = viewer.locator("canvas[data-evidence-canvas]")
            canvas_size = await canvas.evaluate("el => ({width: el.width, height: el.height})")
            require(canvas_size["width"] > 0 and canvas_size["height"] > 0, "PDF canvas rendered with zero dimensions")
            await viewer.locator(".evidence-locator-note").wait_for(timeout=20_000)
            await page.wait_for_timeout(300)
            locator_text = await viewer.locator(".evidence-locator-note").inner_text()
            overlay_count = await viewer.locator(".evidence-pdf-overlay").count()
            require(overlay_count > 0, f"PDF source quote did not receive a bbox/text-match highlight: {locator_text}")
            await page.screenshot(path=str(OUT_DIR / "day5-staging-evidence-pdf-1440x1000.png"), full_page=True)
            results["screenshots"].append("day5-staging-evidence-pdf-1440x1000.png")
            require(worker_responses, "The PDF.js .mjs module worker was not requested by the real browser")
            require(all("javascript" in (item["content_type"] or "").lower() for item in worker_responses),
                    f"The PDF.js worker did not return JavaScript MIME: {worker_responses}")
            require(pdf_responses, "The source PDF was not fetched by the real browser")
            results["evidence"] = {"canvas": canvas_size, "locator": locator_text, "overlay_count": overlay_count,
                                   "worker_responses": worker_responses, "pdf_responses": pdf_responses}
            results["checks"]["evidence_pdf_worker_and_quote_highlight"] = "PASS"
            await page.locator(".modal-close").click()

            responsive: dict[str, dict[str, int | bool]] = {}
            for width, height in ((1440, 1000), (1280, 900), (768, 1024), (390, 844)):
                await page.set_viewport_size({"width": width, "height": height})
                await page.wait_for_timeout(300)
                measurement = await page.evaluate("({viewport: window.innerWidth, document: document.documentElement.scrollWidth, body: document.body.scrollWidth})")
                overflow = int(measurement["document"]) > int(measurement["viewport"]) + 1
                responsive[f"{width}x{height}"] = {**measurement, "horizontal_overflow": overflow}
                if width in (1440, 390):
                    name = f"day5-staging-brief-{width}x{height}.png"
                    await page.screenshot(path=str(OUT_DIR / name), full_page=True)
                    results["screenshots"].append(name)
            require(not any(item["horizontal_overflow"] for item in responsive.values()),
                    f"The public page has horizontal document overflow: {responsive}")
            results["responsive"] = responsive
            results["checks"]["responsive_1440_1280_768_390"] = "PASS"

            await page.goto(PREVIEW_URL, wait_until="networkidle", timeout=60_000)
            await page.get_by_text("Public backend not configured", exact=True).wait_for(timeout=20_000)
            await page.get_by_role("button", name=re.compile("Open Verified Golden Run", re.I)).click()
            await page.get_by_label("Verified Golden provenance").wait_for(timeout=30_000)
            final_storage = await page.evaluate("localStorage.length")
            require(final_storage == 0, f"Static fallback unexpectedly depended on localStorage: {final_storage}")
            results["checks"]["refresh_reloads_static_golden_without_storage"] = "PASS"

            health_probe = await page.request.get(f"{PREVIEW_URL}/health", timeout=10_000)
            api_probe = await page.request.post(f"{PREVIEW_URL}/api/simulate", data="{}", headers={"Content-Type": "application/json"}, timeout=10_000)
            require(health_probe.status == 503 and health_probe.headers.get("x-causora-backend-status") == "not-configured",
                    f"Static-only /health route was not explicitly blocked: {health_probe.status}")
            require(api_probe.status == 503 and api_probe.headers.get("x-causora-backend-status") == "not-configured",
                    f"Static-only /api route was not explicitly blocked: {api_probe.status}")
            require((await health_probe.json()).get("error", {}).get("code") == "backend_not_configured",
                    "Static-only /health response did not identify the missing backend")
            require((await api_probe.json()).get("error", {}).get("code") == "backend_not_configured",
                    "Static-only /api response did not identify the missing backend")
            results["direct_backend_probes"] = {"/health": health_probe.status, "/api/simulate": api_probe.status,
                                                "response_code": "backend_not_configured"}
            results["checks"]["static_only_direct_routes_blocked"] = "PASS"

            api_requests = [url for url in requests if "/api/" in url or urlparse(url).path.endswith("/health")]
            results["api_requests"] = api_requests
            require(not api_requests, f"Static-only public preview attempted backend requests: {api_requests}")
            results["checks"]["static_only_no_backend_requests"] = "PASS"
            results["console_errors"] = console_errors
            require(not console_errors, f"Browser console errors were observed: {console_errors}")
            results["checks"]["browser_console"] = "PASS"
            results["status"] = "PASS"
        except Exception as error:
            results["status"] = "FAIL"
            results["failure"] = f"{type(error).__name__}: {error}"
            results["api_requests"] = [url for url in requests if "/api/" in url or urlparse(url).path.endswith("/health")]
            results["console_errors"] = console_errors
            raise
        finally:
            output = OUT_DIR / "day5_public_preview_acceptance.json"
            output.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            await context.close()
            await browser.close()
            print(json.dumps(results, indent=2, ensure_ascii=False))


asyncio.run(main())
