# Day 4 Task Matrix — Source Requirements

This file records the user-provided Day 4 brief and the relevant `Causora.pdf` requirements as the implementation baseline. It is a checklist, not a completion claim.

## Sources

- User-provided Day 4 brief inherited in the task context (2026-10-08), especially the scope/dependencies, Day 1–3 compatibility, Brief/Evidence/failure/Golden Run requirements, English/responsive acceptance, and package/manifest delivery requirements. The user message is not duplicated as a separate source file.
- `docs/Causora.pdf`, page 16: Golden Run shell, health checks, short timeout, service wake-up guidance, cached-demo fallback, and accurate source/mode labels (quoted by the user brief).
- `Causora.pdf`, page 22: Ding's Day 4 work is “Brief UI, Evidence click, error states, Golden Run shell”; G4 is “first real E2E,” and Simulation remains viewable after a later failure.
- `Causora.pdf`, pages 19–23: strong targets, demonstration expectations, G4/team responsibility, and acceptance boundaries. Strong targets are not to be mislabeled as independent hard requirements.

## Personal Day 4 acceptance checklist

| Requirement | Must remain true |
|---|---|
| Five-stage flow | Data Intake → Scenario Lab → Decision Matrix → AI Boardroom → Decision Brief. |
| Scope boundary | Ding owns the frontend/integration work. Do not replace Deng's Monte Carlo engine or Wang's Critic/Synthesizer/numeric-scan/fallback policy. |
| Shared contracts | Keep v1 requests/errors and v2 simulation success validation as currently defined; no silent breaking DTO changes. |
| Identity binding | Bind downstream Boardroom/Brief/Evidence/decisions to the current simulation ID, dataVersion, scenario ID, and matching request/review/policy/release context. Invalidate stale downstream state. |
| Decision Brief | Consume a matching validated Boardroom response; derive displayed metrics and recommendation eligibility from the validated Simulation/selection; reject unknown references or failed numeric guardrail. Distinguish no-feasible, not-yet-run, blocked, and service failure. |
| Human decision | Approve/Reject are local human records only, bound to the current run/option and clearly labelled as browser-local; never imply purchase, supplier contact, or signed agreement. Change assumptions must navigate to editable assumptions and invalidate downstream state. |
| Evidence | Clicks preserve Evidence IDs/source binding; show source file, page, raw quote, quote-match method/score, and bbox only when valid. Keep human confirmation, quote-match status, and model assumption distinct. Handle missing record/file, invalid page/locator, timeout, and PDF load failure with retry/return paths. |
| Formula Trace | Keep existing trace tied to the same simulation/scenario/option; never fall back to a different run's formula data. |
| Failure preservation | A later AI/Boardroom/Critic failure must not erase a successful Matrix, cost breakdown, Delta, or Formula Trace. Retry AI without re-running simulation. Ignore stale/late responses. |
| Golden shell | Health check, short timeout, wake-up guidance, live retry, and clearly labelled saved-example fallback. Static Day 1/2 data is not a real verified E2E Golden. Only cache a real matching reviewed end-to-end run after success. |
| Modes | Accurately distinguish LIVE, LIVE · SAME-FAMILY REVIEW, LIVE SIMULATION · AI REVIEW UNAVAILABLE, and CACHED · VERIFIED GOLDEN RUN. Do not promote unreviewed development output. |
| English/accessibility | New file names, source comments, docs, UI labels, and error text are English. Support keyboard focus/close/return/retry. |
| Responsive checks | Inspect 1440, 1280, 768, and 390 px; no page overflow, clipped headings/buttons, overlaps, or modal/quote failure. Matrix may scroll locally. |
| Browser/HTTP verification | Install dependencies; run typecheck, lint, full regression, new tests, production build and production-preview smoke. Exercise real backend HTTP; browser evidence and fault-injection evidence must be distinguished from test fixtures. Production PDF acceptance must click the source quote and verify the PDF.js worker MIME and rendered page. |
| Package | `Causora_Day4_Ding_Xiangfeng.zip`, complete source without secrets, `node_modules`, or virtual environments; include acceptance report, changelog, team handoff, dependency note, tests/logs/screenshots, SHA-256 manifest, and verified unzip/start instructions. |

## Independent QA follow-up — Ding-owned findings

| Finding | Fix and verification |
|---|---|
| P1: production PDF worker `.mjs` served as octet-stream | Added `text/javascript; charset=utf-8`; static smoke asserts the worker response, and Chromium opens `EV-014` page 4 from the production static preview, renders the canvas, and highlights the exact quote. |
| P2: Boardroom `{{token}}` body left uninterpolated | Added strict token/`metrics[]` validation and plain-text rendering from the selected option's current Simulation and scenario; unit tests cover `{{delta_tco}}`, declared references, and invalid/unbound tokens. |
| P2: unmatched quote could satisfy Verified Golden | Evidence remains viewable, but cache creation and reloading both require `quoteMatched === true`; tests include `quoteMatched=false, matchScore=0` and a recomputed cache digest. |
| P2: Boardroom browser headers/CORS absent from handoff | Added exact provider/Critic header values and `Access-Control-Expose-Headers`/allow-list requirements to `API_CONTRACT.md` and the Day 4 team handoff. |
| P2: frontend SHA list stale | Regenerated `frontend/MANIFEST.sha256` after all frontend changes; the package-root integrated manifest is also regenerated after staging. |

## Team G4 boundary

G4 is not passed by a simulation-only response or offline/test fixture. To claim G4, one real reviewed simulation must flow through real Boardroom/Critic/Synthesizer and guarded Brief, Evidence, a human decision, with failure preservation demonstrated. Keep G4 pending if required team endpoints or approvals are unavailable.
