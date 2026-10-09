> Technical fix status (2026-10-07): See the integrated package root TECHNICAL_FIX_REPORT.md. Original pending templates remain historical. Wang's supplied confirmation is preserved at backend/backend/reviewed/wang-2026-10-07. Model policy and release still require team confirmation.

# Wang Hao Day 3 — Latest Monte Carlo Service Integration

**English owner-module ZIP. Latest target: `Causora-DengJinzhu-Day3-Integrated(1).zip`.**

This revision replaces the Day1/Day2 v6 deterministic development target with Jinzhu's actual **HTTP `POST /api/simulate` Monte Carlo service**. It sends a v1 request and validates the v2 response containing simulation, deltas, selections, traces and executionContext. No backend core or Ding frontend file was changed or included as an overlay.

All analysis remains **UNREVIEWED DEVELOPMENT ONLY**, with the original executionContext preserved, `decisionReady=false`, and every successful role `DEV_ONLY`. Actual Monte Carlo computation on synthetic unapproved inputs is **not** real-world data validation, a recommendation or human approval.

## Delivered

- `mc_client.py`: fresh HTTP requests, explicit opt-in, no mock/cache fallback, immutable request/response/header/digest captures.
- `mc_validation.py`: original v1 request/v2 response schemas plus identity, probability/service denominators, P90 rank, component/rounding closure, nine deltas, non-decision selection-shape consistency and unreviewed provenance checks.
- `mc_roles.py`: concurrent CFO/COO/Risk calls, narrow strict typed projections, canonical JSON Pointer metric bindings, code-authored claims, isolated provider failures/timeouts and propagated outer cancellation.
- `mc_review_compat.py`: native `reviewed_contract.json` / `review_record.json` verification using the actual latest backend verifier. Safe pending-form mapping, not an approval generator.
- `mc_examples/`: **four actual newly requested HTTP captures**, twelve all-scenario offline-selector analyses, and one actual three-role MODEL_PROXY smoke.
- Critic fixtures retained: **12 development cases. 30 blind held-out inputs with separate labels**. Labels remain draft/independently unreviewed.
- English runbook, integration instructions and actual test records. Latest Wang suite: **98 passed** with the latest backend source root. Backend original suite: **63 passed and 37 subtests passed**.

See `reports/MC_INTEGRATION_RUNS.md`, `reports/VALIDATION_REPORT.md` and `reports/MODEL_SMOKE_REVIEW.md`.

## 1. Start Jinzhu's latest service unchanged

Extract the supplied Jinzhu Day3 archive into a separate directory. Work in its `backend/` directory, not Wang's directory:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/start_unreviewed_dev.py --host 127.0.0.1 --port 8000
```

Windows PowerShell, inside that same backend directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -X utf8 -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 scripts\start_unreviewed_dev.py --host 127.0.0.1 --port 8000
```

Use the supplied dedicated launcher. It sets the exact development switch, clears approval variables and isolates unreviewed trace artifacts. Do not fake a reviewed record or set `TEAM_APPROVED` to make development work.

```bash
curl http://127.0.0.1:8000/health
curl -H 'Content-Type: application/json' --data-binary @examples/simulate_request_v1.json \
  http://127.0.0.1:8000/api/simulate
```

This returns real 1,000-run / 104-week v2 MC results with UNREVIEWED markers. The source data and policy remain synthetic/unapproved. Outside this launcher, the original formal mode remains fail-closed. The tested current formal request returned v1 HTTP 503.

## 2. Install Wang's module separately

Open a second terminal **inside this extracted `wanghao-day3/` directory**:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Use Python 3.11+. On Windows replace `.venv/bin/python` with `.\.venv\Scripts\python.exe -X utf8`.

The Wang client does not import or compute with Jinzhu's engine. Backend dependencies, including NumPy, are installed only in the backend's environment. Optional model keys belong only on a trusted server. None are bundled.

## 3. Fetch a new MC response and analyse one scenario

```bash
.venv/bin/python -m agent_day3.mc_cli fetch-analyse \
  --enable-unreviewed-dev --base-url http://127.0.0.1:8000 \
  --request mc_examples/http_base/request.json \
  --capture ../fresh-mc-capture --scenario baseline --provider offline \
  --out ../fresh-baseline-analysis.json
```

The `--capture` directory and output file must be new. This always makes a new service request. There is no old fixture fallback. The offline provider is an explicitly named **deterministic claim selector**, not AI output. Statistics still come from the actually computed HTTP result.

Analyse the other scenarios from the same immutable full response:

```bash
.venv/bin/python -m agent_day3.mc_cli analyse --enable-unreviewed-dev \
  --capture ../fresh-mc-capture --scenario demand-drop --provider offline \
  --out ../fresh-demand-drop-analysis.json

.venv/bin/python -m agent_day3.mc_cli analyse --enable-unreviewed-dev \
  --capture ../fresh-mc-capture --scenario lead-stress --provider offline \
  --out ../fresh-lead-stress-analysis.json
```

To change inputs, use `mc_examples/http_demand_changed/request.json` or `mc_examples/http_lead_changed/request.json` and run **fetch-analyse again** with new output names. Do not edit the request inside a saved capture. Its digest binds the originally sent body. Changing it or pairing old results with changed demand/lead/seed is rejected.

`dataVersion` is the source dataset version and may legitimately remain the same across input changes. New simulationId, requestId and request/result hashes identify the new computation. Browser-style JSON numeric spellings (`1` instead of `1.0`) were also requested and tested. Canonical hashes preserve the actual representation without rejecting valid numeric shares.

## 4. Optional actual model provider

With authorized `OPENAI_API_KEY` and `OPENAI_API_BASE` on the server:

```bash
.venv/bin/python -m agent_day3.mc_cli analyse --enable-unreviewed-dev \
  --capture ../fresh-mc-capture --scenario demand-drop \
  --provider model --model gpt-5-mini --out ../model-demand-drop-analysis.json
```

The CLI checks the live model catalog. CFO/COO/Risk calls run concurrently. A provider selects only code-verified claim IDs. It cannot author numbers, prose, new options, recommendations or approval. All statements and metric values are rendered from validated role-local inputs. `ALL_READY` means three valid development outputs, **not semantic completeness or formal acceptance**.

## 5. Test and verify

For tests involving the actual latest backend verifier/source files, set its backend directory:

```bash
CAUSORA_DAY3_BACKEND=/absolute/path/to/latest/backend .venv/bin/python -m pytest -q
.venv/bin/python scripts/verify_latest_backend.py --backend-root /absolute/path/to/latest/backend
```

Windows:

```powershell
$env:CAUSORA_DAY3_BACKEND = (Resolve-Path ..\Causora-DengJinzhu-Day3-Integrated\backend).Path
.\.venv\Scripts\python.exe -X utf8 -m pytest -q
```

Without that source directory, captured-result/role/Critic tests remain independent, but the two real-source native-review tests explicitly skip. A skip is not a source-verifier integration pass. `pytest.ini` deliberately excludes four historical v6 deterministic-engine regression files, preventing the old engine from becoming the default integration target.

Optional v1 baseline compatibility check (not a frontend build):

```bash
.venv/bin/python scripts/check_contract_types.py
npm ci --ignore-scripts --no-audit --no-fund
npm run test:contract
```

`reference/jinzhu_day3/` holds original v1 request/v2 response schemas and the supplied v2 TypeScript candidate for **server-side development validation only**. Ding owns any jointly approved frontend migration. Wang did not change the shared production contract or frontend files.

## 6. Review format and remaining work

The latest formal review pair is `reviewed_contract.json` plus `review_record.json`. See `evidence_review/FORMAL_REVIEW_FORMAT.md` for verification, derived-field source mapping, old-format limits and the prepared **pending-only** draft. Eleven human decisions remain pending, reviewer/timestamp empty. The older Day2 verifier stays available only as legacy compatibility. It is no longer described as the current native format.

Still pending: genuine human sign-off, team policy approval, three-owner v2 release/Ding frontend integration, independently reviewed Critic labels, and future full Critic/Synthesizer/final Numeric Guardrail. No Day4 implementation or final Boardroom/approval is fabricated.

Historical deterministic samples/reports are under `reports/prior_deterministic_revision/`. Old mock mode remains explicitly LOCAL_MOCK and is not used by `mc_cli`. **Do not run the old `dev_cli`/v6 bootstrap as the current integration path.**

The owner-only archive includes SHA-256 integrity checking via `scripts/verify_package.py`. Do not overlay its package files onto either teammate's project.
