# Day 1 Readiness Audit — v4.1 Encoding & Gate Clarification

**Judgment:** Wang's AI + Evidence **Day 1 mock handoff passes controlled local checks**. The team's collective **G1 mock walkthrough has not received an owner's recorded signoff**, which is different from saying a real simulator or signed legal review is required on Day 1. See [`day1_acceptance.md`](day1_acceptance.md) for observed commands and screenshots.

| Boundary | Status | Meaning |
| --- | --- | --- |
| Wang Day 1 synthetic evidence, schema, provider smoke and mock | **PASS** | Six matched page-4 internal clauses, selectable PDF, provider proxy report, pending mock and **50 Python tests**. A non-UTF-8 default encoding emulation also passed all 50 after explicit UTF-8 reads. |
| Xiangfeng v4.1 static frontend mock compatibility | **PASS for demonstrated scope** | Five v4.1 evidence IDs, camelCase/units, original TS validator, prior frontend build and browser Evidence/Boardroom/Brief walkthrough. PDF navigation opens **page 4**. Internal ledger retains source bboxes, but no frontend rectangle highlight yet. |
| Team owner signoff of **mock** G1 walkthrough | **NOT RECORDED** | Integration lead should witness/acknowledge the static mock flow. Real calculation and manual evidence approval are **not** conditions for this Day 1 acceptance. |
| Original v4.1 UI wording and mock `Approve D1` | **UX CAUTION** | “Verified” refers to demo/import state, not individual human-reviewed clauses. Make that distinction and mock-only action explicit before suggesting external approval. This is not proof of Day 1 failure. |
| Real clause approval / production BusinessVariable promotion | **PENDING — later** | Day 1 `manually_verified:false` and no promoted Wang variables are deliberate and correct. Review claims before treating them as verified production facts. |
| Real simulator, backend, agents/fallback, optional PDF-region highlight | **NOT TESTED — later** | Static mock covers this Day 1 integration handoff. Deterministic computation may legitimately report `monteCarloRuns:0`. Zero describes the absence of Monte Carlo draws, not the absence of calculation. Production run provenance must be checked separately. |

**Owner follow-up:** Xiangfeng can sign off the mock demonstration without waiting for Jinzhu's simulator or clause-by-clause human approval. Later, review actual business evidence, connect backend and deterministic/stochastic computation, and decide whether to add bbox highlighting. Xiangfeng's *unsigned* original `API_CONTRACT.md` currently says production simulation always has a positive run count. That sentence should be clarified with the team to allow deterministic execution with zero draws. This revision does **not** edit the original Xiangfeng ZIP.
