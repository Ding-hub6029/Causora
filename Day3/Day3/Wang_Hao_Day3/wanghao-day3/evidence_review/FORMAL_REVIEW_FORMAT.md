# Native Day3 review format — aligned to the supplied latest backend

## Canonical current formal pair

The current format is **`reviewed_contract.json` + `review_record.json`**, exactly as Jinzhu's supplied `backend/config/templates/reviewed_bundle_FORMAT.md` and `app.release_verifiers.verify_reviewed_bundle_record` specify. Wang now provides `agent_day3.mc_review_compat.verify_latest_review_bundle` using that actual verifier in an isolated process. This is adoption of the provided format, not a claim that a separate external discussion or human sign-off occurred.

The review bundle must contain all 16 exact contract fields, a separate PDF source/file SHA, and a field-level provenance map for every field. The record must bind the canonical contract and field-provenance hashes, identify its real reviewer/time/reference, and list completed review items. Wang's wrapper additionally requires the exact six evidence IDs plus five assumptions, closes provenance item references, verifies actual source files stay inside the supplied backend root and checks their SHA-256 values. Source-file SHA and review-record SHA are **different**, not interchangeable.

```bash
python -m agent_day3.mc_cli verify-review-native \
  --backend-root /path/to/latest/backend --review-bundle /path/to/genuinely-reviewed-pair
```

The output verifies only record/contract integrity. It is not a recommendation, policy approval, trace release, authenticated person identity or final acceptance. This positive genuine-human path was **not exercised**, because no genuine signed pair was supplied. Rejection of pending data was exercised both by Wang and the original latest backend verifier.

## Current delivered draft — deliberately fails the formal gate

`data/native_day3_pending/` contains:

- `draft_reviewed_contract.json`: different pending kind, not the formal reviewed filename/kind.
- `pending_review_record.json`: all eleven items `pending`, no reviewer ID/reference/time, no confirmed values.

It was produced by `prepare_pending_native_review` from the existing source-bound AI candidate and unchanged original human form. It checks both owners' raw synthetic PDF/notice/demo JSON hashes first. It **does not** sign, mark reviewed, approve a dataset or configure the backend formal environment.

Even renaming the draft files to the official filenames fails both verifiers. Do not change pending to reviewed as a development workaround.

Recreate a draft in a new directory if needed:

```bash
python -m agent_day3.mc_cli review-draft --enable-unreviewed-dev \
  --backend-root /path/to/latest/backend --out /new/pending-draft
```

## Field mapping semantics

`FIELD_PLAN` in `mc_review_compat.py` declares every primary source and dependency:

- Contract clauses use their original EV identifiers and PDF SHA.
- Demonstration dates and locked forecast use **`ASSUMPTION:<key>`** identifiers and frozen synthetic JSON, not fabricated PDF evidence.
- Notice status/source use the correspondence log and the `noticeSent` review item.
- Derived `daysToRenewal`, `noticeDeadline`, `renewalLocked`, `minPurchaseUnitsA` and `evidenceIds` retain an explicit `derivedFromReviewItemIds` dependency list. One primary evidence ID is not claimed to prove all dependencies.
- The conditional clause EV-020 remains an internal human-review requirement. No new frontend evidence field is added.

The draft's extra pending/dependency fields are **internal review worksheet metadata**, not public API amendments. Jinzhu's present verifier accepts nonempty source identifiers for assumption provenance, but the human reviewer/owners should confirm the semantic mapping before completing the formal pair. No claim is made that an assumption has become a legal clause or observed real-world fact.

## Legacy Day2 compatibility

The retained `review_compat.py` still verifies an original Day2 manifest/receipt through its original verifier, without creating approval. It is no longer the latest backend's native review format.

An old manifest or an AI candidate **cannot automatically become the native reviewed pair**: native field provenance, record bindings and derived-item dependencies must be explicitly supplied/checked. The provided safe compatibility route maps the existing candidate into the **pending** native worksheet. It preserves its candidate dataVersion and does not relabel it as the current MC output's dataVersion. Once the real human signs off, the owners should create the required native pair from that agreed source/provenance, then run the actual verifier. No positive old-to-native auto-approval converter is included.

The older formal v1 snapshot route still requires a reviewed DatasetSuccess/evidence snapshot and a non-trivial simulation-owner verifier. A native two-file contract record alone is not a full DatasetSuccess. This revision does not fabricate missing public evidence/variable DTOs to make that older route pass. The new MC development route cannot enter that formal path.

See `LEGACY_DAY2_REVIEW_FORMAT.md` only for historical workflow details. Genuine human review, team policy approval and the three-owner v2 release remain deferred. Development HTTP calculations use none of these approvals.
