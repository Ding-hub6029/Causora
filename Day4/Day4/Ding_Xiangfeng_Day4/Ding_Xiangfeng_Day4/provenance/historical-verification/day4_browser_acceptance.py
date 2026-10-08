#!/usr/bin/env python3
"""Real-browser Day 4 smoke checks; requires Python Playwright and Chromium.

Set CAUSORA_PREVIEW_URL to the local or temporary preview origin. The screenshots
are evidence of this specific run, not team approval or a formal G4 record.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

BASE_URL = os.getenv("CAUSORA_PREVIEW_URL", "http://127.0.0.1:3000").rstrip("/")
def default_api_base() -> str:
    configured = os.getenv("CAUSORA_API_BASE_URL", "").strip()
    if configured:
        return configured.rstrip("/")
    parts = urlsplit(BASE_URL)
    hostname = parts.hostname or ""
    if hostname.startswith("3000-"):
        return f"{parts.scheme}://8000-{hostname[5:]}"
    if hostname in {"127.0.0.1", "localhost"}:
        return f"{parts.scheme}://{hostname}:8000"
    raise RuntimeError("Set CAUSORA_API_BASE_URL when the preview host is not a local Sandbox service.")

API_BASE = default_api_base()
CHROMIUM = os.getenv("CAUSORA_CHROMIUM", "/usr/bin/chromium")
EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
VIEWPORTS = [(1440, 900), (1280, 720), (768, 1024), (390, 844)]

async def page_metrics(page):
    return await page.evaluate("""() => {
      const visible = (node) => {
        const r = node.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight;
      };
      const insideHorizontalScroller = (node) => {
        for (let parent = node.parentElement; parent; parent = parent.parentElement) {
          const style = getComputedStyle(parent);
          if (['auto','scroll'].includes(style.overflowX) && parent.scrollWidth > parent.clientWidth + 2) return true;
        }
        return false;
      };
      const outOfBounds = [...document.querySelectorAll('button,a,h1,h2,h3')]
        .filter((node) => visible(node) && !insideHorizontalScroller(node))
        .map((node) => ({node, rect: node.getBoundingClientRect()}))
        .filter(({rect}) => rect.left < -1 || rect.right > innerWidth + 1)
        .map(({node, rect}) => ({tag: node.tagName, text: (node.innerText || node.getAttribute('aria-label') || '').trim().slice(0, 60), left: Math.round(rect.left), right: Math.round(rect.right)}));
      const localScrollers = [...document.querySelectorAll('*')]
        .filter((node) => node.clientWidth > 0 && node.scrollWidth > node.clientWidth + 2)
        .map((node) => ({className: typeof node.className === 'string' ? node.className : '', client: node.clientWidth, scroll: node.scrollWidth, overflowX: getComputedStyle(node).overflowX}))
        .filter((entry) => ['auto','scroll'].includes(entry.overflowX))
        .slice(0, 8);
      return {viewport: innerWidth, pageWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth, outOfBounds, localScrollers};
    }""")

async def matrix_page(page, width: int, height: int):
    await page.set_viewport_size({"width": width, "height": height})
    await page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=45_000)
    await page.locator(".backend-health-panel.healthy").wait_for(timeout=8_000)
    await page.get_by_role("button", name=re.compile("Decision Matrix", re.I)).click()
    matrix_marker = page.get_by_text("OPTION × SCENARIO MATRIX", exact=False).first
    await matrix_marker.wait_for(timeout=10_000)
    await matrix_marker.scroll_into_view_if_needed()
    await page.wait_for_timeout(350)
    metrics = await page_metrics(page)
    target = EVIDENCE_DIR / f"matrix-{width}x{height}.png"
    await page.screenshot(path=str(target), full_page=False, animations="disabled")
    return metrics, target

async def main():
    results = {"preview": BASE_URL, "api_base": API_BASE, "viewports": [], "layout_issues": [], "live_e2e": {}}
    browser_errors: list[str] = []
    browser_console_issues: list[str] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path=CHROMIUM, headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context()
        health_response = await context.request.get(f"{API_BASE}/health", timeout=15_000)
        health_payload = await health_response.json()
        assert health_response.status == 200 and health_payload.get("data", {}).get("service") == "ready", "backend health check did not report ready"
        assert "NOT DECISION-READY" in health_payload.get("data", {}).get("banner", ""), "development health check did not disclose its non-reviewed mode"
        results["health"] = {"status": health_response.status, "service": health_payload["data"]["service"], "mode": health_payload["data"]["simulation"], "missing_reasons": health_payload["data"]["missingReasons"], "banner": health_payload["data"]["banner"]}
        for width, height in VIEWPORTS:
            page = await context.new_page()
            page.on("pageerror", lambda error: browser_errors.append(str(error)))
            page.on("console", lambda message: browser_console_issues.append(f"{message.type}: {message.text[:400]}") if message.type in ("warning", "error") else None)
            metrics, target = await matrix_page(page, width, height)
            results["viewports"].append({"width": width, "height": height, "metrics": metrics, "screenshot": str(target)})
            if metrics["pageWidth"] > width + 1 or metrics["outOfBounds"]:
                results["layout_issues"].append({"width": width, "height": height, "pageWidth": metrics["pageWidth"], "outOfBounds": metrics["outOfBounds"][:8]})
            await page.close()

        page = await context.new_page()
        await page.set_viewport_size({"width": 1440, "height": 900})
        page.on("pageerror", lambda error: browser_errors.append(str(error)))
        page.on("console", lambda message: browser_console_issues.append(f"{message.type}: {message.text[:400]}") if message.type in ("warning", "error") else None)
        await page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=45_000)
        await page.locator(".backend-health-panel.healthy").wait_for(timeout=8_000)
        health_panel = await page.locator(".backend-health-panel.healthy").inner_text()
        assert "unreviewed development only" in health_panel.lower()
        assert "gates remain pending" in health_panel.lower()
        await page.get_by_role("button", name=re.compile("Decision Matrix", re.I)).click()
        live_button = page.get_by_role("button", name=re.compile("Run simulation", re.I))
        await page.wait_for_function("() => { const b = [...document.querySelectorAll('button')].find(x => /Run simulation/i.test(x.innerText)); return !!b && !b.disabled; }", timeout=5_000)
        await page.get_by_role("button", name=re.compile("Run simulation", re.I)).click()
        await page.get_by_text("UNREVIEWED — DEVELOPMENT ONLY", exact=False).first.wait_for(timeout=60_000)
        await page.get_by_text("1,000 Monte Carlo runs", exact=False).first.wait_for(timeout=10_000)
        await page.locator(".toast").wait_for(state="hidden", timeout=6_000)
        first_body = await page.locator("body").inner_text()
        first_match = re.search(r"sim-dev-unreviewed-[a-z0-9]+", first_body)
        assert first_match, "first simulation identity is missing"
        first_id = first_match.group(0)
        first_request = re.search(r"req-[a-z0-9]+", first_body)
        assert first_request, "first request identity is missing"

        await page.get_by_role("button", name=re.compile("Demand −15%", re.I)).click()
        browse_body = await page.locator("body").inner_text()
        assert first_id in browse_body and first_request.group(0) in browse_body, "matrix browsing cleared or replaced the current run"
        browse_screenshot = EVIDENCE_DIR / "matrix-browse-preserves-live-1440x900.png"
        await page.screenshot(path=str(browse_screenshot), full_page=False, animations="disabled")

        await page.get_by_role("button", name=re.compile("Scenario Lab Variables", re.I)).click()
        demand_input = page.locator('input[aria-label="Demand shock"]')
        demand_before = await demand_input.input_value()
        await demand_input.focus()
        await demand_input.press("ArrowRight")
        demand_after = await demand_input.input_value()
        assert demand_after != demand_before, "demand input did not change"
        edited_body = await page.locator("body").inner_text()
        assert first_id not in edited_body, "assumption edit left stale simulation visible"
        edit_screenshot = EVIDENCE_DIR / "scenario-input-invalidates-1440x900.png"
        await page.screenshot(path=str(edit_screenshot), full_page=False, animations="disabled")

        await page.get_by_role("button", name=re.compile("^03 Decision Matrix", re.I)).click()
        await page.get_by_role("button", name=re.compile("Run simulation", re.I)).click()
        await page.get_by_text("UNREVIEWED — DEVELOPMENT ONLY", exact=False).first.wait_for(timeout=60_000)
        await page.get_by_text("1,000 Monte Carlo runs", exact=False).first.wait_for(timeout=10_000)
        live_body = await page.locator("body").inner_text()
        second_match = re.search(r"sim-dev-unreviewed-[a-z0-9]+", live_body)
        assert second_match and second_match.group(0) != first_id, "input change did not produce a fresh simulation identity"
        identity_text = second_match.group(0)
        await page.locator(".toast").wait_for(state="hidden", timeout=6_000)
        await page.locator(".matrix-panel").evaluate("el => window.scrollTo(0, window.scrollY + el.getBoundingClientRect().top - 88)")
        await page.wait_for_function("Math.abs(document.querySelector('.matrix-panel').getBoundingClientRect().top - 88) < 3", timeout=5_000)
        live_screenshot = EVIDENCE_DIR / "live-matrix-1440x900.png"
        await page.screenshot(path=str(live_screenshot), full_page=False, animations="disabled")
        live_body = await page.locator("body").inner_text()
        assert "NOT DECISION-READY" in live_body
        assert "No approval, Boardroom result, or recommendation is created." in live_body
        results["live_e2e"]["simulation"] = {"status": "passed", "identity": identity_text, "warning_visible": True, "screenshot": str(live_screenshot)}
        results["live_e2e"]["matrix_browse"] = {"status": "passed", "same_simulation_id": first_id, "same_request_id": first_request.group(0), "screenshot": str(browse_screenshot)}
        results["live_e2e"]["assumption_edit"] = {"status": "passed", "demand_shock": {"before": demand_before, "after": demand_after}, "stale_result_cleared": True, "new_simulation_id": identity_text, "screenshot": str(edit_screenshot)}

        async def inject_simulation_503(route):
            await route.fulfill(status=503, content_type="application/json", body=json.dumps({
                "schemaVersion": "causora.contract.v1",
                "requestId": "req-day4-fault-injection",
                "error": {"code": "provider_unavailable", "message": "Injected HTTP 503 for Day 4 failure-preservation acceptance.", "requestId": "req-day4-fault-injection"},
            }))

        await page.route("**/api/simulate", inject_simulation_503)
        await page.get_by_role("button", name=re.compile("Run simulation", re.I)).click()
        await page.get_by_text("Live simulation was not applied.", exact=False).wait_for(timeout=20_000)
        failed_retry_body = await page.locator("body").inner_text()
        assert identity_text in failed_retry_body and "1,000 Monte Carlo runs" in failed_retry_body, "failed retry erased the last validated Matrix result"
        assert "The previous validated live 3×3 Matrix and Formula Trace remain visible" in failed_retry_body
        failure_screenshot = EVIDENCE_DIR / "simulation-retry-preserves-live-1440x900.png"
        await page.screenshot(path=str(failure_screenshot), full_page=False, animations="disabled")
        await page.unroute("**/api/simulate", inject_simulation_503)
        await page.locator(".toast").wait_for(state="hidden", timeout=6_000)
        results["live_e2e"]["simulation_retry_failure"] = {"status": "passed", "fault": "browser route injected HTTP 503 once; not a backend fixture", "retained_simulation_id": identity_text, "retained_matrix_and_trace": True, "result_mode_label": "UNREVIEWED DEV · NOT DECISION-READY", "latest_request_error_visible": True, "screenshot": str(failure_screenshot)}

        await page.get_by_role("button", name=re.compile("Open live Boardroom", re.I)).click()
        await page.get_by_text("REVIEW GATE CLOSED", exact=True).wait_for(timeout=10_000)
        await page.wait_for_function("window.scrollY === 0", timeout=5_000)
        boardroom_body = await page.locator("body").inner_text()
        assert "REVIEW GATE CLOSED" in boardroom_body
        assert "No approval, Critic, Synthesizer, or decision brief is permitted." in boardroom_body
        boardroom_screenshot = EVIDENCE_DIR / "boardroom-gated-1440x900.png"
        await page.screenshot(path=str(boardroom_screenshot), full_page=False, animations="disabled")
        await page.get_by_text("REVIEW GATE CLOSED", exact=True).scroll_into_view_if_needed()
        boardroom_gate_screenshot = EVIDENCE_DIR / "boardroom-gate-details-1440x900.png"
        await page.screenshot(path=str(boardroom_gate_screenshot), full_page=False, animations="disabled")
        results["live_e2e"]["boardroom"] = {"status": "correctly_blocked", "reason": "unreviewed simulation; policy/release pending; no downstream backend endpoint", "screenshots": [str(boardroom_screenshot), str(boardroom_gate_screenshot)]}

        await page.get_by_role("button", name=re.compile("Decision Brief", re.I)).click()
        await page.get_by_text("The simulation, Matrix, and Formula Trace remain available.", exact=False).wait_for(timeout=10_000)
        await page.wait_for_function("window.scrollY === 0", timeout=5_000)
        brief_body = await page.locator("body").inner_text()
        assert "Approval remains disabled while required review/policy/release gates are pending." in brief_body
        assert "Human action" in brief_body and "Disabled" in brief_body
        assert await page.get_by_role("button", name=re.compile("Record human approval|Record rejection", re.I)).count() == 0
        brief_screenshot = EVIDENCE_DIR / "brief-gated-1440x900.png"
        await page.screenshot(path=str(brief_screenshot), full_page=False, animations="disabled")
        await page.locator(".brief-gate-panel").scroll_into_view_if_needed()
        brief_gate_screenshot = EVIDENCE_DIR / "brief-gate-details-1440x900.png"
        await page.screenshot(path=str(brief_gate_screenshot), full_page=False, animations="disabled")
        await page.get_by_role("button", name="Change assumptions").click()
        scenario_nav = page.locator(".stage-nav-item[aria-current='step']")
        await scenario_nav.filter(has_text="Scenario Lab").wait_for(timeout=10_000)
        await page.locator('input[aria-label="Demand shock"]').wait_for(state="visible", timeout=10_000)
        await page.wait_for_function("window.scrollY === 0", timeout=5_000)
        results["live_e2e"]["brief"] = {"status": "correctly_blocked", "decision_actions": "not rendered before matching reviewed Boardroom", "current_simulation_retained_for_view": identity_text, "change_assumptions_navigated_to_scenario_lab": True, "screenshots": [str(brief_screenshot), str(brief_gate_screenshot)]}

        await page.get_by_role("button", name=re.compile("Data Intake", re.I)).click()
        pdf_failure_mode = {"active": True}

        async def inject_pdf_failure_until_retry(route):
            if pdf_failure_mode["active"]:
                await route.fulfill(status=503, content_type="text/plain", body="Injected PDF load failure until Day 4 retry acceptance.")
            else:
                await route.continue_()

        await page.route("**/demo/supplier_a_agreement.pdf", inject_pdf_failure_until_retry)
        await page.get_by_role("button", name=re.compile("Open source quote", re.I)).click()
        await page.get_by_role("button", name="Retry PDF load").wait_for(timeout=20_000)
        await page.get_by_text("The source PDF could not be loaded", exact=False).wait_for(timeout=10_000)
        pdf_failure_mode["active"] = False
        await page.get_by_role("button", name="Retry PDF load").click()
        await page.get_by_text("No bbox was supplied; the highlight was derived from an exact text match", exact=False).wait_for(timeout=30_000)
        canvas = page.locator("canvas[aria-label='PDF page 4']")
        await canvas.wait_for(state="visible", timeout=10_000)
        evidence_screenshot = EVIDENCE_DIR / "evidence-pdf-page-4-1440x900.png"
        await page.screenshot(path=str(evidence_screenshot), full_page=False, animations="disabled")
        evidence_body = await page.locator("body").inner_text()
        assert "If written notice is not received at least 60 days before renewal" in evidence_body
        assert re.search(r"Quote match", evidence_body, re.I) and re.search(r"Human confirmation", evidence_body, re.I)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(500)
        mobile_evidence_metrics = await page_metrics(page)
        modal_box = await page.locator(".detail-modal").bounding_box()
        canvas_box = await canvas.bounding_box()
        quote_box = await page.get_by_text("If written notice is not received at least 60 days before renewal", exact=False).first.bounding_box()
        assert mobile_evidence_metrics["pageWidth"] <= 391 and not mobile_evidence_metrics["outOfBounds"], f"mobile Evidence modal overflows: {mobile_evidence_metrics}"
        assert modal_box and modal_box["x"] >= -1 and modal_box["x"] + modal_box["width"] <= 391, "Evidence modal exceeds the 390px viewport"
        assert canvas_box and canvas_box["x"] >= modal_box["x"] and canvas_box["x"] + canvas_box["width"] <= modal_box["x"] + modal_box["width"] + 1, "PDF canvas is clipped horizontally inside the modal"
        assert quote_box and quote_box["x"] >= modal_box["x"] and quote_box["x"] + quote_box["width"] <= modal_box["x"] + modal_box["width"] + 1, "Evidence quote is clipped horizontally inside the modal"
        mobile_evidence_screenshot = EVIDENCE_DIR / "evidence-pdf-page-4-390x844.png"
        await page.screenshot(path=str(mobile_evidence_screenshot), full_page=False, animations="disabled")
        await page.locator(".modal-close").focus()
        await page.keyboard.press("Shift+Tab")
        focus_inside = await page.locator(".detail-modal").evaluate("el => el.contains(document.activeElement)")
        assert focus_inside, "Shift+Tab escaped the Evidence dialog focus trap"
        await page.keyboard.press("Escape")
        await page.get_by_role("dialog").wait_for(state="hidden", timeout=10_000)
        restored_focus = await page.evaluate("() => document.activeElement?.getAttribute('aria-label') || document.activeElement?.textContent?.trim().slice(0,80) || ''")
        assert "Open source quote" in restored_focus, f"Escape did not restore focus to the evidence trigger: {restored_focus}"
        await page.unroute("**/demo/supplier_a_agreement.pdf", inject_pdf_failure_until_retry)
        results["live_e2e"]["evidence"] = {"status": "passed", "record": "EV-014", "page": 4, "locator": "exact source-text match; no API bbox supplied", "pdf_fault_injected_before_retry": True, "retry": "passed after disabling the injected 503", "screenshots": [str(evidence_screenshot), str(mobile_evidence_screenshot)]}
        results["live_e2e"]["keyboard_modal"] = {"status": "passed", "focus_trap": focus_inside, "escape_closed": True, "restored_focus": restored_focus}

        offline_page = await context.new_page()
        await offline_page.set_viewport_size({"width": 1440, "height": 900})
        async def inject_health_failure(route):
            await route.fulfill(status=503, content_type="application/json", body=json.dumps({"error": {"code": "waking", "message": "Injected cold-start health failure."}}))
        await offline_page.route("**/health", inject_health_failure)
        await offline_page.goto(BASE_URL + "/", wait_until="domcontentloaded", timeout=45_000)
        await offline_page.locator(".backend-health-panel.waking").wait_for(timeout=8_000)
        waking_text = await offline_page.locator(".backend-health-panel.waking").inner_text()
        assert "Server waking up" in waking_text
        assert "not a verified Golden Run" in waking_text
        await offline_page.get_by_role("button", name=re.compile("^03 Decision Matrix", re.I)).click()
        blocked_live_button = offline_page.get_by_role("button", name="Waiting for /health")
        await blocked_live_button.wait_for(timeout=10_000)
        assert await blocked_live_button.is_disabled(), "Live Run remained enabled while backend health was unavailable"
        await offline_page.get_by_role("button", name=re.compile("Open saved example.*not verified E2E", re.I)).click()
        await offline_page.get_by_text("SAVED EXAMPLE · NOT VERIFIED E2E", exact=True).first.wait_for(timeout=10_000)
        await offline_page.get_by_role("button", name=re.compile("^03 Decision Matrix", re.I)).click()
        saved_readonly_button = offline_page.get_by_role("button", name="Golden Run is read-only")
        await saved_readonly_button.wait_for(timeout=10_000)
        assert await saved_readonly_button.is_disabled(), "The saved example must remain read-only"
        health_fallback_screenshot = EVIDENCE_DIR / "golden-health-wakeup-fallback-1440x900.png"
        await offline_page.screenshot(path=str(health_fallback_screenshot), full_page=False, animations="disabled")
        results["live_e2e"]["golden_health_shell"] = {"status": "passed", "health_probe": "browser-injected HTTP 503", "wakeup_guidance": True, "live_run_disabled_until_ready": True, "unverified_saved_example_label": True, "saved_example_read_only": True, "screenshot": str(health_fallback_screenshot)}
        await offline_page.close()

        await page.close()
        await context.close()
        await browser.close()
    expected_fault_console = [issue for issue in browser_console_issues if "503 (Service Unavailable)" in issue]
    unexpected_console_issues = [issue for issue in browser_console_issues if "503 (Service Unavailable)" not in issue]
    results["browser_errors"] = browser_errors
    results["expected_injected_503_console_errors"] = len(expected_fault_console)
    results["browser_console_issues"] = unexpected_console_issues
    assert not browser_errors, f"browser runtime errors: {browser_errors}"
    assert not unexpected_console_issues, f"unexpected browser console issues: {unexpected_console_issues}"
    print(json.dumps(results, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
