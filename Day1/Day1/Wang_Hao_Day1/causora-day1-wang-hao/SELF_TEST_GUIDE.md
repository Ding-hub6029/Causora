# Self-Test Wang's Causora Day 1 v4.1 Handoff

**In plain terms:** There are **two** synthetic contracts in this ZIP. The one-page `supplier_a_poison_pill.pdf` is the old independent regression fixture. The **six-page** `integration_v4.1/public/demo/supplier_a_agreement.pdf` is the only source used by Xiangfeng's v4.1 UI. The UI sample's numeric results and D1 recommendation are copied **LOCAL MOCK** values, not Wang/Jinzhu simulation.

1. Extract the ZIP, open a terminal in its top-level `causora-day1-wang-hao` directory, install Python 3.12, and create a virtual environment:

   ```bash
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install -r requirements.txt
   export PYTHONPATH=src
   ```

   On Windows use `py -3.12 -m venv .venv`, `.venv\Scripts\Activate.ps1` and `$env:PYTHONPATH = "src"` in PowerShell. Do not bypass machine-wide security policies if activation is blocked; call `.venv\Scripts\python.exe` directly instead. JSON text reads/writes in the package explicitly specify `encoding="utf-8"`; do **not** need to change your system locale or enable a global UTF-8 setting.

2. Run `python -m pytest -q tests`. Expected on the recorded environment: **50 passed**. The original 13 test cases are still present, with 37 additional regression executions. Windows PowerShell may additionally run `python -X utf8=0 -m pytest -q tests` to check under its default ANSI code page; expect the same 50 passing tests. We simulated a non-UTF-8 default on Linux and obtained **50 passed**, but have **not** run an actual Windows host. Any red failure is **FAIL**, not something to ignore.

3. Open the **six-page** `demo_data/integration_v4.1/public/demo/supplier_a_agreement.pdf` in a PDF viewer and go to **page 4**. You should be able to select the sentence about 60 days, the 24-month renewal/14% price, the 60% minimum and the $25,000 fee. Then run:

   ```bash
   python -m causora_day1.evidence demo_data/integration_v4.1/public/demo/supplier_a_agreement.pdf demo_data/integration_v4.1/evidence_summary.json --baseline-mock demo_data/integration_v4.1/causora_day1_mock_baseline.json
   python -m causora_day1.make_mock
   python -m causora_day1.front_schema
   python -m causora_day1.adapter
   ```

   Expected: `Matched 6/6 claims; manual signoff remains pending`; the sixth (EV-020) is auto-renew preserved **internally**. All records have `manually_verified:false`, `business_variables:[]`. `internal_pending_mock.json` has **3 scenarios × 3 options = 9** pending cells, no numeric KPI, and `brief.recommended_option_id:null`. The frontend-compatible JSON has **five** v4.1 IDs, `matchScore:1.0`, page 4, LOCAL MOCK label and the **baseline's** illustrative D1 and numeric matrix. It must not be described as a real computed result. Real source bboxes/hash remain in `provenance_ledger.json` even though the frontend DTO has `locatorBbox:null`.

4. If you have Xiangfeng's original v4.1 ZIP, extract it to a **separate** directory, then run `npm ci` inside its `causora/` folder. Return to this Wang package and run `node scripts/verify_v41.mjs /absolute/path/to/causora`. Expected: `PASS baseline v4.1 validateMockData` and a second PASS for hashes, pending state and LOCAL MOCK. Do not edit or overwrite Xiangfeng's original ZIP.

5. In the **temporary** adapted preview (if still active), open the Evidence modal: EV-014 should say page 4 and link to the six-page PDF's page 4. **The true bbox coordinates are retained internally; highlighting the rectangle in the frontend is a later integration task, not a Day 1 mock failure.** Open AI Boardroom: all three Wang role texts should say they await simulation, Critic is a hypothesis. Open Brief: D1 must be visibly labelled an **Xiangfeng baseline mock**, not a Wang-approved recommendation. The original UI still says “Verified starting point” and shows `Approve D1` on mock data: treat this as a **mock-UX caution**, not proof that a person approved evidence.

6. **Optional model smoke:** Only with your team's authorisation and server-side compatible proxy variables, run `python -m causora_day1.provider_smoke --output reports/provider_smoke_current.json`. Four `ok:true` values demonstrate basic proxy connectivity. They do not verify direct OpenAI/Google keys, real agents or fallback. Never share keys or a filled `.env`.

**Day 1 versus later:** This Day 1 ZIP's mock checks pass; ask the integration lead to sign off the **mock walkthrough**, not a real simulation. Human approval is required **later, before promoting real `BusinessVariable` facts**. The Jinzhu computation, backend and optional PDF-region highlighting are also later work. `monteCarloRuns:0` may describe either this static mock **or** a genuine deterministic calculation; require execution provenance rather than judging by this counter. Team G1 mock signoff was **not recorded**; later live E2E readiness is a separate gate. See `reports/day1_acceptance.md` for exact statuses.
