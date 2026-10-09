# Day 2 review data — rebased to Ding Day 3

> Latest Day3 native review format is documented in `FORMAL_REVIEW_FORMAT.md`. `data/native_day3_pending/` contains mapped draft files only, all eleven pending with no signer. The current actual Monte Carlo integration is in the root README and `mc_examples/`. It does not consume this AI ledger as an approved dataset or replace its candidate version.

**Completed here:** an AI-assisted, source-bound review of the six contract evidence items and five explicit demonstration assumptions. The matching pipeline was rerun against the supplied frozen PDF. All eleven are internally consistent **as synthetic demonstration inputs**. This is not Wang Hao's signature, a human review, legal validation or proof of supplier facts.

## Delivered data

| Artifact | Purpose | Boundary |
| --- | --- | --- |
| `data/reviewed_data.json` | Contract, five public `EvidenceRecord` objects with genuine PDF coordinates, and five existing public `BusinessVariable` objects | Internal candidate. **not** `DatasetResult`, `ApiSuccess`, or an endpoint response. `LOCAL_MOCK`, human review pending, decision not ready. |
| `data/review_ledger.json` | Eleven individual review outcomes, source references, normalization notes and pending reasons | AI review is separate from human confirmation and real-world verification. |
| `data/evidence_summary.json` | Six typed records including internal EV-020. Quote text, page, source digest, span and locator | All six quote-matched. Every `manually_verified` remains false. No promoted internal BusinessVariables. |
| `data/human_review_request.json` | Scope-bound eleven-row human confirmation request | Blank name/time and all decisions pending. No generated attestation. |

The candidate has a **new immutable dataVersion**, because its evidence coordinates differ from the frozen UI mock. The original fixture and its simulation are unchanged. Do not attach that new version to copied mock metrics or reuse the old Day 2 review scope.

## Review outcomes

| Item | Reviewed synthetic value | Source / interpretation | Human status |
| --- | --- | --- | --- |
| EV-014 | 60 days | PDF p.4: advance written-notice condition | Pending |
| EV-019 | 24 months | PDF p.4: renewed term | Pending |
| EV-021 | 14% (`0.14` wire fraction) | PDF p.4: renewed-term unit-price uplift. Book once as premium | Pending |
| EV-024 | 60% (`0.6` wire fraction) | PDF p.4: minimum commitment. Forecast basis is separately configured | Pending |
| EV-027 | USD 25,000 integer | PDF p.4: early exit **during the renewed term**, not an unconditional fee on every option | Pending |
| EV-020 | Conditional auto-renew clause present | PDF p.4 renewal text interpreted with EV-014 notice condition. Clause presence does not alone establish lock | Pending |
| decisionDate | 2026-10-04 | Explicit frozen demo configuration, not PDF-derived date | Pending |
| renewalDate | 2026-11-18 | Explicit frozen demo configuration, not PDF-derived date | Pending |
| noticeSent | `false` boolean | Supplied **synthetic** correspondence register only | Pending |
| forecastBasis | `locked-at-renewal` | PDF p.4 explicit synthetic fixed renewal forecast and frozen configuration | Pending |
| lockedForecastUnits24m | 26,000 integer units | Explicit synthetic forecast. **not** historical demand sum or estimator output | Pending |

The code recomputes the deadline **2026-09-19**, the configured **45 days** to renewal, the **15,600-unit** floor and the conditional renewal lock. These are date/constraint derivations, **not** a supply-chain simulation. The fixed 60/40 diversified split and demand-shock cost aggregates remain the team's illustrative mock, not a computed inventory result.

## What stays pending and why

- **PDF-required human per-field review:** no identifiable human confirmation was supplied. AI review never sets `manually_verified=true`, fills a person's name or creates an approved receipt.
- **Real notice status and real contract applicability:** the documents and register are explicitly synthetic. This bundle cannot establish whether a real notice was received, whether a real agreement was signed, or whether its interpretation applies to a real supplier.
- **Computation is outside this ledger:** the latest Jinzhu package now provides real MC development calculations, captured separately under `mc_examples/`. This AI ledger itself computes/certifies no TCO, probability, P90, final Brief or genuine team E2E result and does not become human-approved because those computations ran.

These pending states are not unexplained failures. They distinguish a completed synthetic audit from unavailable external confirmations.

## Jinzhu integration

For **synthetic development**, explicitly require `kind == CAUSORA_AI_REVIEWED_SYNTHETIC_INPUT_CANDIDATE`, inspect `sourceMode`, `permittedUse`, `humanReviewStatus`, `scopeSha256` and source digests, then read `contract`, `evidence` and `variables`. Do not send the complete candidate as a public v1 DTO. Its metadata is an **offline sidecar**, not new HTTP fields.

For a future human-reviewed dataset, the backend owns promotion into the **unchanged** `DatasetResult` shape. It must obtain all eleven confirmations for the current sources, create a new immutable snapshot and record the provenance outside the public DTO. The Day 3 agent module then requires a human review receipt and Jinzhu's result verifier before accepting `SIMULATION_READY` (see `agent_day3/INTERFACE_HANDOFF.md`). JSON receipts are a trusted-server boundary, not cryptographic authentication of a human.

**EV-020 policy:** the current contract has five public evidence IDs and five public BusinessVariables. EV-020 is deliberately retained in the six-record internal ledger. `renewalLocked` is the activation signal. Some raw reviewer notes describe its absence in the UI as a possible gap. That is **not** an approved change request: no sixth public record or new field was introduced here.

## Reproduce without previous ZIPs

From this package root:

```bash
python -m pip install -r requirements.txt
python -m pytest -q evidence_review/tests
python -m evidence_review.pipeline --out /tmp/wang-review-check
```

On Windows use a fresh output folder such as `review-check` and `python -X utf8`. The CLI refuses to overwrite an existing nonempty review folder. Frozen source edits are rejected. Change/version/review sources intentionally instead of silently accepting them.
