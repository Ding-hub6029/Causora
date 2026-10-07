# Causora Day 1 v4 — Delivery and verification

The v4 source and static production export are built from Causora-Day1-Delivery-v3.zip. The original ZIP is unchanged. This release is a corrected Day 1 local mock frontend and a review-ready API proposal; no live backend or participant booking is fabricated.

## Audit corrections

The API now defines typed envelopes, requests, per-scenario selections, selected/no-feasible Brief unions, deterministic ties and ordered violations. Dataset upload v1 is synchronous (200 ready or documented error); an asynchronous 202 protocol is excluded until separately specified. Boardroom requests/responses bind scenarioId and immutable simulation/data version. Owners still need to approve the proposal together.

The runtime validates required shapes, types, versions, references, dates, matrix identities, allocation ratios, cost sums and contract inputs before any local view renders. Invalid bundled input displays an unavailable-approval error. Golden activation additionally verifies its SHA-256. The successful local adapter and no-feasible API DTO remain distinct. A dedicated no-feasible preview hides the winner narrative and blocks approval.

Stockout/service deltas preserve fractional percentage points; money retains exact non-round amounts. CFO token rendering follows the sign of cost difference, including equal cost. Unbound numeric template claims are rejected visibly. Unknown tokens are flagged, never invented. Critic copy now uses “changes by −15%”, qualifies D1 purchases, and distinguishes 2,340 units above the rolling A-floor benchmark from 3,900 total procurement units above realised demand. The 26,000-unit locked forecast is labelled a synthetic PDF-page-4 assumption; historical CSV demand totals 25,936. Holding/stockout components remain disclosed illustrative aggregates.

Static serving now supplies PDF, CSV and XLSX MIME types. Historical screenshots are isolated under artifacts/history-v3; they are not claimed as current evidence. The unused brand configuration uses a packaged local asset.

## Verification

21 automated tests cover the original PDF/quote checks and nine matrix traces plus malformed-input rejection, unknown schema version, fractional deltas, reversed/equal costs, per-scenario winners, no-feasible selection, inclusive limits, deterministic ties, Golden tampering, forecast provenance and real HTTP serving/content types/source-path protection. Lint, typecheck and production build are required before packaging. Current execution/browser results are appended below after verification.

## Human work still required

Xiangfeng must obtain 2–3 real participant confirmations and fill USER_TESTING_KIT.md. The three owners must approve API_CONTRACT.md and the synthetic business interpretation. The release does not claim these have happened, or claim completed full G1 sign-off. Live simulation, Evidence Validator, agent/provider pipeline and HTTP integration belong to Day 2+.


## Executed release checks

Node 22.23.3: lint passed, typecheck passed, build passed; 21/21 tests passed with no skips. Node 24.19.0 also passed the test suite and build earlier in this revision. No original archive was modified.

The final static browser walkthrough verified all five stages and all 20 state-preview combinations (loading/empty/error/no-feasible). No-feasible approval was disabled and the winner narrative was absent in every stage. Golden activation succeeded through hash verification; changing a scenario removed its cache label. Formula text/components/notes rendered without unresolved or rejected tokens. The evidence stack had all five entries and EV-019 opened; Tab/Shift+Tab stayed in the dialog, Escape closed it and restored the trigger. A 13% risk-threshold draft disabled approval and removed the previous approval. The revised Critic displayed both the 2,340 rolling-floor difference and 3,900 total procurement excess.

390/768/1024/1200px viewport checks found no document-level horizontal overflow and retained the local-mock badge. Matrix tables deliberately scroll inside their panels on phones. Browser error logs were empty. Formal screen-reader certification and live backend tests were not performed.

On Windows, START_PREVIEW.cmd serves the included out/ using an installed Node runtime; it requires no npm installation for preview. Open http://127.0.0.1:3000 after the server starts. Keep the command window open. Source development uses the README npm instructions.

Clean-package verification: extracted the candidate ZIP into a new directory; offline npm ci --ignore-scripts installed 314 packages. Under Node 22.23.3, lint, typecheck, 21/21 tests and production build all passed. The final ZIP uses this clean rebuild. The Windows preview helper also finds the installed Codex bundled Node runtime if node is absent from PATH.
