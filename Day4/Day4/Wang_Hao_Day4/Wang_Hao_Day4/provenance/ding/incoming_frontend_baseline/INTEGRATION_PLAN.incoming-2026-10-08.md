# Day 4 three-owner integration plan

## Source roles and merge rule

| Owner/source | Authoritative scope retained in this integration | Merge treatment |
| --- | --- | --- |
| Ding Xiangfeng latest package | `frontend/` public API, page flow, TypeScript contracts, PDF.js rendering, static build and user-facing behavior | Baseline project tree; no page or frontend-contract replacement. |
| Deng Jinzhu previous Day 4 delivery | Monte Carlo engine, v1 request/v2 Matrix + Trace response, reviewed/dev gates, Formula Trace generation, source evidence and HTTP simulation lifecycle | Preserved from the Ding baseline where byte-identical; Deng's Day4 route/evidence additions are merged selectively. |
| Wang Hao latest package | `agent_day4/`, OpenRouter transport, numeric/evidence/business guards, provider budget journal, current pipeline and HTTP Boardroom adapter | Imported as a distinct owner module and merged into the common Boardroom adapter/service rather than overwriting the frontend. |

## Required source mapping

| PDF / G4 item | Owner output | Integration proof planned |
| --- | --- | --- |
| Python/NumPy simulation, `N=1,000` development and `N=10,000` demo target | Deng Monte Carlo engine | Fresh fixed-seed benchmark at both run counts; no algorithm change. |
| Matrix plus Formula Trace identity | Deng v2 response and traces | Contract tests and registration identity checks across nine cells. |
| Source file, page, quote and `quote_matched` evidence | Deng source catalog + Wang evidence validator | Fresh PDF source/quote validation and PDF.js-compatible locator test for EV-024. |
| CFO/COO/Risk parallelism, Critic and Synthesizer | Wang `agent_day4.pipeline` | Imported module tests and timeout/cancellation tests; no Monte Carlo rerun in AI path. |
| Numeric/evidence validation and no invented options | Wang validation modules | Provider-output validation tests and retained server selection. |
| Simulation-first Boardroom request and fail-closed review | Shared service/adapter | Simulation repository binds request/result/contract/evidence; formal AI requires reviewed, current, decision-ready v2 run. |
| Provider timeout within frontend deadline | Wang pipeline + Ding frontend | One global forty-second pipeline deadline; per-stage deadlines receive remaining time; frontend remains forty-five seconds. |
| Evidence click/highlight | Ding locator + Deng/Wang source lookup | Backend converts PyMuPDF top-left rectangles to PDF.js bottom-left user space; browser/E2E verification is scheduled. |
| Human approvals/Golden Run | Team records | Remain pending and fail closed; development data is never upgraded. |

## Delivery sequence

1. Start from Ding's latest frontend baseline and keep its public contracts/pages unchanged.
2. Import Wang's latest isolated `agent_day4` implementation and required runtime dependencies.
3. Merge Wang's current simulation repository/Boardroom adapter with Deng's Matrix/Trace service lifecycle.
4. Correct evidence coordinate convention and add source-backed locator checks.
5. Add reproducible Monte Carlo benchmarks and API/AI failure-path regression coverage.
6. Run fresh backend, agent and frontend verification; only then generate English reports, manifests and the final ZIP.
