# Apply Wang Hao Day 2 Without Taking Over Teammates' Work

This ZIP is **Wang's additive overlay**, not a replacement team ZIP. Keep each user-supplied source archive untouched.

## Merge into a separate working copy

1. Extract the supplied `Causora_Day2_Ding_Xiangfeng_Improved_v2(1).zip` into a **new temporary working directory**, giving you a `causora/` root. Confirm `causora/lib/contracts.ts`, `causora/demo_data/causora_day1_mock.json`, `causora/public/demo/supplier_a_agreement.pdf` and `causora/API_CONTRACT.md` exist.
2. Open the supplied `Day1.zip`. From its nested **`Deng Jinzhu——Day 1.zip`**, copy **only** the unchanged `causora/simulation_day1/` directory under that same working `causora/`. Do not replace Ding's shared `API_CONTRACT.md`, `lib/`, Golden Run or UI mock.
3. Extract **this** Wang Day 2 ZIP into the directory **containing** `causora/`. It adds `causora/evidence_day2/` and `causora/causora_day1/` (Wang's own unchanged Day 1 dependency). It should not overwrite `app/`, `components/`, `lib/`, `demo_data/`, `public/`, `simulation_day1/` or `golden/`.
4. Keep `Causora(1).pdf` as the **requirements specification**. The evidence source is Ding's separate **six-page synthetic supplier PDF**, not the specification itself.

## Cross-owner sanity checks

From the merged working `causora/` root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r evidence_day2/requirements-test.txt
python -m pytest -q evidence_day2/tests
python -m unittest discover -s simulation_day1/tests -q
python -m evidence_day2.cli preprocess --project-root . --out /tmp/causora-wang-day2-pending
```

On Windows use `py -3.12 -m venv .venv`, then `.venv\Scripts\python.exe -m pip install -r evidence_day2\requirements-test.txt` and `.venv\Scripts\python.exe -m pytest -q evidence_day2\tests`. To preprocess use a **new empty directory path** such as `C:\temp\causora-wang-day2-pending` instead of `/tmp/...`. The source code explicitly reads UTF-8; our non-UTF-8 test was emulated on Linux, not executed on a Windows host. `evidence_day2/requirements-tested.txt` records exact top-level versions observed in our test environment; its dependencies are not hash-pinned.

**Expected:** 38 Wang Day 2 tests pass, Jinzhu Day 1's 16 tests pass; PDF page 4 gives six quote matches (five v1 UI evidence IDs and internal EV-020). The pending output has **zero** approvals and **no** `dataset_success.json`. The exact pending form shipped with this ZIP is bound to the supplied Ding/Jinzhu source byte hashes and Wang's code/DTO version; if either owner changed a source fixture or contract since this build, **do not edit the digest**: review/version the changes and regenerate the request.

Optional Ding static frontend checks (run in the merged `causora/` root with Node.js 22): `npm ci && npm run typecheck && npm run lint && npm test && npm run build && npm run test:production`. These are the frontend owner's existing checks; Wang does not change or claim ownership of their UI.

## Review is not automated

To complete **Wang's manually reviewed demo fields**, a real reviewer must inspect the synthetic supplier PDF **page 4** and separate mock notice-register CSV, then independently confirm all six clauses and five assumptions. See [`causora/evidence_day2/HUMAN_REVIEW_GUIDE.md`](causora/evidence_day2/HUMAN_REVIEW_GUIDE.md). Only after that, submit their *own* completed review JSON:

```bash
python -m evidence_day2.cli promote \
  --project-root . \
  --review /path/to/human_completed_review.json \
  --out /path/to/NEW_reviewed_dataset
python -m evidence_day2.cli verify --project-root . --bundle /path/to/NEW_reviewed_dataset
```

The post-review dataset is a **separate, self-attested synthetic** version; it cannot be paired with Jinzhu's unchanged Day 1 static matrix or silently injected into Ding's static frontend. No direct HTTP backend or production authentication is included. Jinzhu's 104-week deterministic Day 2 engine and joint G2 signoff remain separate team dependencies, not Wang code in this archive.
