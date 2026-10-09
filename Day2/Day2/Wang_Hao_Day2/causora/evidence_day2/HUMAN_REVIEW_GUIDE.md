# Wang Day 2 — Human Review of the Synthetic Demo Contract

**Status:** PENDING. No human has signed the enclosed `examples/pending_review/review_request.json`. Machine `quote_matched=true` means that text and typed values were located in the PDF. It is **not** an attestation that a real supplier's facts are true.

## What to open

1. Open [`supplier_a_agreement.pdf`](../public/demo/supplier_a_agreement.pdf), **page 4 of 6**. It visibly says *SYNTHETIC / NOT A REAL CONTRACT*.
2. Open the separate [`supplier_correspondence_log.csv`](../public/demo/supplier_correspondence_log.csv). This is also synthetic. It records **no valid timely written non-renewal notice**. Absence of a notice in this demo CSV does **not** establish absence of a real-world email or letter.
3. Open [`review_request.json`](examples/pending_review/review_request.json). The `scopeSha256` binds the exact PDF, CSV, UI mock, source assets, claim-extraction/promotion code, shared validator/schema, contract type and quote/page/value set. Do not change any quote, page, expected value, ID, source hash, implementation hash or scope digest to make a check pass.

## Review each PDF field yourself

| Evidence ID | Source excerpt on PDF p. 4 | Value to check | Simulated field after review |
| --- | --- | --- | --- |
| EV-014 | “If written notice is not received at least 60 days before renewal, the agreement automatically renews.” | **60 days**. Conditional on no timely notice | `renewalNoticeDays = 60` |
| EV-019 | “The agreement automatically renews for 24 months at a 14% higher unit price.” | **24 months** | `renewalTermMonths = 24` |
| EV-021 | Same sentence as EV-019 | **14%**. Convert to fraction **0.14** once | `renewalPriceIncreasePct = 0.14` |
| EV-024 | “The renewed term has a minimum purchase commitment equal to 60% of forecast demand.” | **60%**. Convert to share **0.6** | `minPurchaseShareA = 0.6` |
| EV-027 | “Early exit during the renewed term incurs a fixed termination fee of $25,000.” | **$25,000** integer USD | `terminationFeeUsd = 25000` |
| EV-020 (internal only) | Same conditional auto-renew sentence as EV-019 | Conditional **auto-renew clause present**. Not a claim of unconditional renewal | Typed internal `auto_renew=true`. No new public v1 field |

Check **five assumptions separately** in the JSON review request: `decisionDate=2026-10-04`, `renewalDate=2026-11-18`, `noticeSent=false` (from the **separate synthetic CSV**), `forecastBasis=locked-at-renewal`, `lockedForecastUnits24m=26000` (PDF p. 4 labels it *for the synthetic scenario only*). The dated deadline is `2026-09-19`. Renewal is locked in the **demo only** because the decision date is later **and** `noticeSent=false`. Historical demand totals 25,936 units and is **not** the source of the 26,000-unit locked forecast.

## How to sign only after actually reviewing

- Make a **separate copy** of `review_request.json`, fill `reviewerName` with your own real name, fill `reviewedAtUtc` with a current UTC ISO timestamp ending in `Z`, and enter this exact statement in `acknowledgement`: **“I reviewed each synthetic contract field and listed assumption. This is not real-world contract verification.”**
- For **each** of the six evidence rows and five assumption rows, set `decision` to `approved` and set `confirmedValue` to **that row's exact `expectedValue`** only if you personally checked it. For an issue, leave `pending` or set `rejected` and add `notes`. The promotion command will refuse it. Do not ask an AI to claim it performed the human review or silently fill approvals.
- In the project root run: `python -m evidence_day2.cli promote --project-root . --review /path/to/your_review.json --out /path/to/new_reviewed_output`. You may alternatively ask the integrator to run the exact reviewed file. The output includes the **exact completed review JSON**, immutable review scope, reviewed internal ledger, five v1 Evidence responses, a typed `DatasetSuccess` envelope, a separate versioned **five-variable** Jinzhu handoff (EV-020 stays only in Wang's six-item ledger), review receipt, and a hash manifest. **Nothing rewrites** Ding's frozen UI mock or Jinzhu's Day 1 fixture.
- From the project root, run `python -m evidence_day2.cli verify --project-root . --bundle /path/to/new_reviewed_output` to re-check the local hashes, exact review, unchanged PDF/CSV/code scope, and generated DTO relationships. This detects accidental substitutions and stale releases. The hashes are **not a digital signature**.
- The receipt is **a self-attestation in a synthetic demo**, not a cryptographic identity proof, legal review, published approval or real-world contract attestation. The completed review travels *inside* the output bundle. Retain your original copy as well. Run a second check against the real app before any production deployment.

If any clause/assumption is not accepted, stop. A quote-matched but unreviewed record must **not** be promoted to a `BusinessVariable`. Team G2 also requires Jinzhu's **actual** deterministic 104-week matrix, which is **not present** in the supplied Day 1 materials.
