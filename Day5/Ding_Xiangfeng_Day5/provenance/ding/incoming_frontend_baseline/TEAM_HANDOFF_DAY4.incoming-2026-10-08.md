# Day 4 Team Handoff — Frontend / Ding Xiangfeng

Date: 2026-10-08  
Status: The five Ding-owned frontend findings from independent QA are fixed and re-tested. The frontend follow-up is ready for personal acceptance; formal team G4 remains **PENDING**.

## What is ready

- Current `/api/simulate` v1 request and strict v2 success validation remain the source of live Matrix/Formula Trace data.
- Frontend-owned Boardroom and Evidence clients validate identity, response version/correlation, scenario, selection, evidence source, page, quote and optional locator without adding or weakening the shared DTOs.
- `AgentOutput.body` accepts only supported, declared `{{token}}` metric references; the view renders those values from the selected option in the same validated Simulation/scenario. It does not display raw model placeholders or use model-supplied numeric substitutions.
- Brief and human decision controls fail closed unless a matching reviewed-v2 Simulation and validated Boardroom pass the numeric guardrail.
- Simulation/Matrix/Formula Trace remain viewable after a later request failure. Browser acceptance covers one injected simulation HTTP 503 and a PDF-load 503 followed by explicit retry.
- Production static serving maps PDF.js `.mjs` files to `text/javascript; charset=utf-8`. The production Chromium acceptance clicks “Open source quote”, loads the worker, renders `EV-014` page 4, and confirms the exact quote highlight.
- Golden persistence rejects test fixtures, incomplete/unreviewed runs, and any cited Evidence with `quoteMatched !== true`; creation and reloading both recheck this condition. Unmatched Evidence remains viewable but is not verification evidence.
- The page-load `GET /health` check is bounded to 2.5 seconds and gates Live Run; a cold/unavailable service shows “Server waking up”, retry guidance, and either a complete reviewed cache or an explicitly non-verified Day 2 saved example. A ready health response does not grant policy/review approval.
- `frontend/MANIFEST.sha256` is current. Test artifacts and screenshots are in `verification/logs/` and `verification/evidence/`; see `DAY4_TEST_REPORT.md` and the root `DAY4_ACCEPTANCE_REPORT.md`.

## Mandatory browser-visible Boardroom headers and CORS

- A successful `POST /api/boardroom` response must include `X-Causora-Provider-Mode: primary` or `same-family-fallback`, plus `X-Causora-Critic-Status: complete`. `unavailable` is reserved for the explicit retryable Critic-unavailable path; missing or unknown values are rejected by the frontend.
- Echo the matching `X-Request-Id` for response correlation. In browser CORS responses, expose all client-read headers: `Access-Control-Expose-Headers: X-Causora-Provider-Mode, X-Causora-Critic-Status, X-Request-Id`. Without this header, browser JavaScript cannot read the two required Boardroom headers and rejects the response.
- For cross-origin calls, allow the exact configured frontend origin, `GET, POST, OPTIONS`, and request headers `Content-Type, X-Request-Id`; Evidence uses GET plus `X-Request-Id`, Boardroom uses JSON POST plus `X-Request-Id`. The clients omit credentials; configure the explicit origin rather than relying on a wildcard.

## Required team-owned integration work — not Ding frontend defects

1. **Deng/backend:** the integrated service currently exposes `/health` and `POST /api/simulate`; it does not expose `POST /api/boardroom` or `GET /api/evidence/{id}`. Implement the approved routes using the existing v1 DTOs, with run/data/scenario identity and request correlation, safe timeouts, accurate errors, the response headers above, and no silent sample fallback.
2. **Wang/agent pipeline:** provide actual authorized Critic/Synthesizer and numeric-guardrail outputs for the same run. A development sidecar or test fixture is not treated as an approved `AgentOutput`; no frontend stub substitutes for the missing service.
3. **Team policy/release owners:** `release-pending/policy_approval.PENDING.json` lists 15 policy topics and has no completed approval record; `release-pending/trace_release.PENDING.json` remains pending with approval slots/reference unfilled. Do not rename or edit either record to claim approval.
4. After the above are supplied, run one real reviewed simulation through Boardroom/Critic/Synthesizer, guarded Brief, Evidence, browser-local human choice, and failure-preservation checks. Only that evidence can move G4 from **PENDING**.

## Verified human-review input

The supplied 11-item Wang confirmation is present and was recognized by the backend's real review verifier during the integration audit. That record does not approve the 15-topic team policy, the v2/trace release, a Boardroom run, or G4.

## Current live behavior

The actual Monte Carlo endpoint returns a marked `unreviewed_development_only` result with `decisionReady=false`. The UI permits viewing this development result and its Matrix/Trace, but it displays the persistent non-decision-ready warning, does not show a formal recommendation/approval action, and blocks Boardroom/Brief. Production PDF acceptance exercises the packaged saved-example record `EV-014`; it does not pretend the missing live Evidence endpoint responded.

The local bundled `golden/golden_run.json` remains the integrity-checked Day 2 saved example, not a verified E2E Golden. A browser-local Verified Golden cache can be written only after reviewed-v2 Simulation + matching Boardroom/Critic + every cited, quote-matched live Evidence record + a same-run browser-local human choice all validate. The current team services cannot complete that flow, so no verified Golden artifact is claimed or fabricated. Human review, policy, release, and G4 stay **PENDING**.
