# Causora Day 1 — Wang Hao / AI + Evidence (v4.1.1; aligned to Xiangfeng v4.1)

**Scope and owner:** This is the AI + Evidence **Day 1** handoff requested by Wang Hao. The original specification names the role holder “Wu Wang”; confirm whether this is the same person in the team roster. Day 1 covers an evidence schema, machine-readable synthetic poison-pill PDF, provider connectivity smoke, and a team mock handoff. This package **does not** implement Day 3–4 production agent orchestration, full numeric guardrails, fallback, a live 104-week simulation, or human approval.

**Single interface baseline:** Xiangfeng Ding's user-supplied `Causora-Day1-Delivery-v4.1(1).zip` (SHA-256 `bafcb910f25d224a0f31d6c2ed8bbcfdcb40873398a164ee4e44b82e66a42fb4`). Its **original ZIP was not modified**. Its `API_CONTRACT.md`, `lib/contracts.ts`, `lib/types.ts`, `lib/validation.ts` and `demo_data/causora_day1_mock.json` govern the frontend DTO. The matching six-page PDF in `public/demo/supplier_a_agreement.pdf` is a **synthetic** source, SHA-256 `1e816c38cae6a045ef8b05426bb4c87ed160f119a52ac8adc65be074ef8c183f`.

## Start here

| File / directory | What it proves or supplies |
| --- | --- |
| `demo_data/integration_v4.1/public/demo/` | Exact copied v4.1 PDF + three other synthetic source artifacts; PDF page 4 is the real UI evidence source. |
| `demo_data/integration_v4.1/causora_day1_mock_baseline.json` | Read-only copy of Xiangfeng's Day 1 numeric/Brief LOCAL MOCK. |
| `demo_data/integration_v4.1/evidence_summary.json` | Six **internal** PDF-bound claims: EV-014, EV-019, EV-021, EV-024, EV-027 plus auto-renew EV-020; `manually_verified=false` throughout; no promoted business variables. |
| `demo_data/integration_v4.1/internal_pending_mock.json` | Wang's **no-simulation** three-scenario × three-option pending matrix; null recommendation. Not a frontend `MockData` or `no_feasible_option` DTO. |
| `demo_data/integration_v4.1/frontend_compatible_local_mock.json` | Frontend `MockData` with v4.1 camelCase fields, IDs, units and Xiangfeng's **pre-existing illustrative** metrics/D1 Brief. Wang's evidence and three role narratives/Critic hypothesis are adapted. No real computation is attributed to Wang/Jinzhu. |
| `demo_data/integration_v4.1/provenance_ledger.json` | Full source SHA-256, actual page-4 source quote/span/bbox, typed extraction/unit, manual-review flags, assumption source, score conversion, and origin of copied mock numbers. **Internal; not a frontend DTO.** |
| `demo_data/integration_v4.1/*.schema.json` | Structural wire-format JSON Schemas; run Python semantic checks and Xiangfeng's TS validator too. |
| `demo_data/supplier_a_poison_pill.pdf`, `demo_data/evidence_summary.json`, `demo_data/mock_e2e.json` | Original **independent one-page fixture** and its internal regression payload. Never mix its page-1 hash/rectangles with v4.1 six-page evidence. |
| `src/causora_day1/` | Schema, semantic checks, conservative PDF matcher, adapter, fixture generators, structural schemas, proxy smoke. |
| `tests/`, `scripts/verify_v41.mjs` | Original 13 test cases plus regressions; direct invocation of Xiangfeng's v4.1 runtime validator. |
| `INTERFACE_MAPPING_v4.1.md`, `CHANGELOG_v4.1.md`, `reports/day1_acceptance.md` | Mapping, defect/fix matrix and observed PASS/FAIL/NOT TESTED results. |
| `CONTRACT_CLARIFICATION_FOR_XIANGFENG.md` | Unapplied owner-review proposal to distinguish deterministic zero-draw runs, static mocks and later acceptance gates. |
| `.env.example`, `reports/tested_versions.md` | Inert placeholders and actually tested dependency versions. No credentials shipped. |

## Reproduce from an extracted ZIP

With Python 3.12 (tested) and the package directory as your working directory:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export PYTHONPATH=src
python -m causora_day1.evidence demo_data/integration_v4.1/public/demo/supplier_a_agreement.pdf demo_data/integration_v4.1/evidence_summary.json --baseline-mock demo_data/integration_v4.1/causora_day1_mock_baseline.json
python -m causora_day1.make_mock
python -m causora_day1.front_schema
python -m causora_day1.adapter
python -m pytest -q tests
```

**Expected:** `Matched 6/6 claims; manual signoff remains pending`; **50 tests passed**, including a regression ensuring all Python text I/O declares UTF-8. The same suite passes with Python's UTF-8 mode disabled and a non-UTF-8 system default, simulating the reported Windows encoding failure. The v4.1 frontend displays **five** evidence IDs; internal auto-renew EV-020 is the sixth. The original one-page fixture can be regenerated separately with `python -m causora_day1.make_fixture demo_data/supplier_a_poison_pill.pdf`, then `python -m causora_day1.evidence demo_data/supplier_a_poison_pill.pdf demo_data/evidence_summary.json`. Do not use it as a frontend contract source.

**Frontend check (optional, requires the separately supplied Xiangfeng v4.1 project):** extract that original baseline ZIP to a separate directory, run `npm ci` in its `causora/` folder, then from this Wang package run `node scripts/verify_v41.mjs /absolute/path/to/causora`. It invokes Xiangfeng's own `validateMockData` against this package's adapted JSON, verifies hashes and mock status. The adapted JSON was also injected into a **throwaway** frontend copy and built with `npm run build`; the original baseline project/ZIP was left unchanged. See `reports/day1_acceptance.md` for browser check and screenshots.

**Optional live proxy smoke:** supply `OPENAI_API_KEY` and `OPENAI_API_BASE` only as server-side environment variables; then run `python -m causora_day1.provider_smoke --output reports/provider_smoke_current.json`. The current result is from the sandbox's configured OpenAI-compatible **proxy**, not independent proof of direct OpenAI/Google vendor keys or deployment. The plain and strict responses of `gpt-5-nano` and `gemini-3-flash-preview` are tested separately. No key or endpoint URL is written to the report.

## Day 1 acceptance versus later work

**Day 1 mock demonstration:** deliver this schema, synthetic selectable-text PDF and page-linked evidence, primary/Critic connectivity probes, a v4.1-valid mock adapter, and a clearly labelled frontend mock walkthrough. The 3×3 pending Wang matrix and Xiangfeng's illustrative numeric mock are distinct. These controlled deliverables can be accepted **without real simulation results or manual clause approval**. Team-wide G1 mock signoff still requires the integration lead to acknowledge the walkthrough; this ZIP alone cannot sign for another person.

**Later production/integration:** verify contract clauses with a person before promoting real `BusinessVariable` records; connect the real backend and a documented 104-week computation; review the approval UI and optionally add PDF region highlighting. These are **not Day 1 mock acceptance blockers**. `monteCarloRuns: 0` means **zero Monte Carlo draws**, not necessarily "no computation": a deterministic simulator can legitimately use zero. Distinguish a static mock from a calculated result by run provenance/labels, actual formula execution and validation, **not that number alone**. Xiangfeng's original unsigned `API_CONTRACT.md` currently says production runs must be positive; the team must explicitly reconcile that sentence with deterministic mode in a later reviewed contract revision. His original ZIP remains untouched.

## Interpretation and limitations

- **Quote match is not human verification.** `LIVE_VERIFIED` is barred unless *every* record is quote-matched, individually human-reviewed and promoted as a matching typed `BusinessVariable`; no fixture is marked verified. In this mock, `business_variables=[]`. Do not change flags just to satisfy a test. The baseline frontend has separate illustrative `variables` for display; those are **not** Wang-approved `BusinessVariable` records.
- The baseline has three external scenarios (`baseline`, `demand-drop`, `lead-stress`), D0=100% A / no exit, D1=60% A + 40% B / no exit, D2=100% B / exit A. Internally pending means **no recommendation**, not `no_feasible_option`. The full frontend sample retains Xiangfeng's clearly labelled LOCAL MOCK D1 and numerical metrics to exercise the unchanged UI, not as Wang/Jinzhu findings.
- The source price quote is **14%** (`percent`); its simulation fraction would be **0.14**. Source minimum is **60%**, internal share **0.6**. The baseline's `demandShock=-15` is a whole percent, money is integer USD, dates are ISO dates. `45` days, no notice, locked forecast 26,000 and floor 15,600 are **synthetic assumptions/derivations**, not solely PDF-verified facts.
- The internal ledger holds the actual page-4 bboxes in **top-left-origin PDF page points**. The v4.1 static frontend imports JSON directly; a non-null JSON coordinate array is inferred as `number[]`, which fails its TS fixed-tuple assertion. The frontend DTO therefore uses `locatorBbox:null` and links to **page 4** without claiming a highlighted rectangle. The full coordinates/hash/source span have **not** been discarded. A reviewed frontend loader/type change and region-highlighting behavior are **later integration work, not Day 1 blockers**.
- Xiangfeng's UI currently contains the phrase “Verified starting point” and an enabled LOCAL MOCK “Approve D1” control, despite Wang's unapproved evidence; **do not present those as human approval**. The adapter's visible Brief guardrail and handoff warning distinguish the mock. This is an **open wording/approval UX caution**, not proof that Day 1 requires signed evidence or computed simulation. Team-wide G1 mock signoff was not obtained from its owner; live E2E approval is a separate later gate.
- The matcher is intentionally limited to controlled English synthetic wording. Ambiguous, scanned, adversarial or real contracts require human/legal review and production upload/security controls. The Day 1 probe does not send source documents to an LLM.

**Further instructions:** [`INTERFACE_MAPPING_v4.1.md`](INTERFACE_MAPPING_v4.1.md), [`TEAMMATE_TEST_WALKTHROUGH.md`](TEAMMATE_TEST_WALKTHROUGH.md), [`SELF_TEST_GUIDE.md`](SELF_TEST_GUIDE.md), and [`reports/day1_acceptance.md`](reports/day1_acceptance.md). Original task spec: Causora v3.0 pp. 20–23.
