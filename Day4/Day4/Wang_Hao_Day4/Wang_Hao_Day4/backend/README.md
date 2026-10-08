# Causora: Deng Jinzhu Day 3 Integrated Backend Delivery

Backend source, runnable interface, v2 schemas/proposals, verifier configuration, tests, reproducible data and regeneration script are combined in this directory. No separate data download is needed. Current team status is in the parent integrated TECHNICAL_FIX_REPORT.md; historical unreviewed fixtures retain their labels.

```text
Causora-DengJinzhu-Day3-Integrated/
  backend/  FastAPI, Day 1-3 sources, schemas, tests, docs, templates
  data/     1,000-run data, matrix/deltas, traces, manifest
  README.md
  INTEGRATED_MANIFEST.sha256
```

1. Enter backend/, read RUNBOOK.md, install dependencies; normal startup is `uvicorn app.service:app --host 0.0.0.0 --port 8000`.
2. Run `pytest -q`. Original delivery reported 63 passed/37 subtests in TEST_REPORT_FINAL.md; the later technical fixes report 70/37.
3. Default POST /api/simulate accepts shared v1 and correctly returns review-gated v1 503. The success path exists but requires validated records.
4. For immediate development-shape testing, run `python scripts/start_unreviewed_dev.py --port 8000` from backend/ (or `python backend/scripts/start_unreviewed_dev.py --port 8000` from this wrapper). It returns v2 200 labelled UNREVIEWED DEVELOPMENT ONLY with decisionReady=false; see DEV_UNREVIEWED_INTEGRATION.md.
5. Real Wang review, Deng/Ding/Wang policy and common-release records must validate per CONFIGURATION_AND_VERIFIERS.md before formal v2 matrix/deltas/selections/nine traces.
6. Reproduce unreviewed delivered data from backend/:

```bash
python scripts/reproduce_deng_day3_data.py \
  --out /tmp/deng-day3-reproduced \
  --expected-manifest ../data/deng_day3_data_manifest.json
```

Historical data/ stays UNREVIEWED/PENDING_11_HUMAN_REVIEW_ROWS/UNAPPROVED_TEST_INPUT, not API success, review, approval or Boardroom input. v2 200 fixtures are TEST_FIXTURE_ONLY, never production evidence. This owner package excludes Ding's pages and supplies backend integration/schema materials only.

| Purpose | File under backend/ unless indicated |
| --- | --- |
| Installation, ports, CORS, remote access | RUNBOOK.md |
| Wang bundle, three-owner policy/release formats | CONFIGURATION_AND_VERIFIERS.md |
| All model policy topics | MODEL_POLICY_CONFIRMATIONS.md |
| v1/v2 migration and Boardroom identity | VERSION_MIGRATION_AND_BOARDROOM_HANDOFF.md |
| Original regression/fresh extraction | TEST_REPORT_FINAL.md |
| Unreviewed 200 development | DEV_UNREVIEWED_INTEGRATION.md |
| Windows UTF-8/LF reproduction | WINDOWS_ENCODING_AND_REPRODUCTION.md |
| Source/data hash relationships | ../data/SOURCE_COMPATIBILITY.md |
