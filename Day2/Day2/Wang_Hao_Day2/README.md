# Wang Hao — Causora Day 2 (AI + Evidence) Only

**Deliverable type:** small **owner-only overlay**, not a copy of the whole team application. This archive contributes Wang's PDF preprocessor, quote-bound source ledger, human-review gate, typed contract/BusinessVariable handoff, tests and documentation. It **does not** include Ding's Day 2 frontend or Jinzhu's Day 1 module, let alone invent Jinzhu's Day 2 simulation engine.

## Scope from the supplied final build specification

`Causora(1).pdf` p. 22 assigns Wang Day 2: **PDF preprocessing + `quote_matched` + manually verified demo fields**. This package implements the executable matching and review/promotion path, but the included review request is intentionally **unsigned and all 11 decisions are `pending`**. Without a real person's check of the synthetic supplier PDF and mock notice register, no releaseable reviewed `BusinessVariable` artifact is generated. Wang's work should **not** be represented as fully human-reviewed yet. Team G2 also requires Jinzhu's real deterministic matrix; that is not Wang's deliverable and is not in either supplied Day 1 package.

## What's actually inside

| Path | Owner / purpose |
| --- | --- |
| `causora/evidence_day2/` | **New Wang Day 2 module**: `pipeline.py`, `handoff_models.py`, `cli.py`, 38 regression tests, JSON Schema, English interface mapping and 11-item pending review form. |
| `causora/causora_day1/*.py` | **Wang's own unchanged Day 1** source dependency, copied byte-for-byte from the supplied Wang ZIP in the three-person `Day1.zip`; included so applying the overlay needs no second Wang install step. |
| `APPLY_TO_TEAM.md` | Non-destructive merge and exact test commands. |
| `WANG_DAY2_TEST_REPORT.md` | Measured results and honest PASS / PENDING boundaries. |
| `WANG_DAY2_MANIFEST.sha256` | SHA-256 for every file in this owner-only archive, except itself. |

**Not included:** Ding source/`out/`, Jinzhu source/oracle, synthetic supplier source PDF or CSV, shared mock, frontend UI, real engine or any approved human review. Those are supplied **separately** by their owners. `evidence_day2/examples/pending_review/evidence_pending.json` and `review_request.json` are **Wang's generated evidence/review artifacts from those frozen team fixtures**, not replacement originals.

## Integration tested but not absorbed

The module imports `simulation_day1.wire_models` and `simulation_day1.build_day1_schemas` from **Jinzhu Day 1** and expects `demo_data/causora_day1_mock.json`, `public/demo/supplier_a_agreement.pdf` and `lib/contracts.ts` from **Ding Day 2 Improved v2**. After overlaying both owners' supplied material as described in `APPLY_TO_TEAM.md`, our checks passed:

- **Wang Day 2:** 38/38 tests (also 38/38 with non-UTF-8 default encoding on Linux); six of six exact synthetic PDF matches; zero approved reviews in the archive.
- **Wang Day 1:** 50/50 in the original separate source root; bundled Python code was byte-identical.
- **Jinzhu Day 1:** 16/16 interface/source tests, **not** his absent Day 2 engine.
- **Ding Day 2:** 24/24 UI/source tests plus one production HTTP check; TypeScript, ESLint and build passed in a separate integration workspace. **No Ding code is included in this overlay.**

A local simulated-review test verifies the **shape and provenance graph** of the future output: five Ding v1 Evidence responses and frontend variables, six internal Wang ledger fields, **five** typed Jinzhu computational variables with conditional EV-020 intentionally kept only in Wang's ledger. `DatasetSuccess` and `EvidenceSuccess` are checked using Jinzhu's actual Pydantic models and schemas. This is **not** an actual human approval, API server, deterministic matrix or legal review. See `causora/evidence_day2/INTERFACE_MATRIX.md`.

## Run and human-review boundary

Follow [`APPLY_TO_TEAM.md`](APPLY_TO_TEAM.md). From a merged `causora/` project root:

```bash
python -m pip install -r evidence_day2/requirements-test.txt
python -m pytest -q evidence_day2/tests
python -m evidence_day2.cli preprocess --project-root . --out /path/to/NEW_pending_review
```

A person who **actually checks** the six clauses plus five synthetic assumptions against the **real fixture PDF page 4** and notice CSV can complete a copy of the pending form per [`HUMAN_REVIEW_GUIDE.md`](causora/evidence_day2/HUMAN_REVIEW_GUIDE.md), then run `python -m evidence_day2.cli promote ...`. No auto-approval is provided. The resulting attestation is explicitly **self-attested synthetic demo review**, not authenticated identity or a real supplier fact. The next command `python -m evidence_day2.cli verify --project-root . --bundle /path/to/NEW_reviewed_output` checks the original review, source/code scope, DTO graph and file hashes; hashes are not a digital signature.

**Final status:** Wang's Day 2 *module, integration contract, negative tests and unsigned review workflow* are ready. **Individual human field review is pending.** Jinzhu's deterministic Day 2 engine, Ding's live UI/API connection, PDF region highlighting and the team-wide G2 signoff are outside this owner-only deliverable.
