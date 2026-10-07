# Unreviewed Development Integration

**UNREVIEWED — DEVELOPMENT ONLY.** Uses packaged synthetic contract and UNAPPROVED_TEST_INPUT policy for actual 1,000-run, 104-week MC. It is not Wang review, team policy approval, v2 release or a decision. Every v2 200 must retain unreviewed markers.

Install requirements.txt, then from backend/:

```bash
# macOS/Linux
python scripts/start_unreviewed_dev.py --port 8000
# Windows CMD
scripts\start_unreviewed_dev.cmd --port 8000
# Windows PowerShell
python .\scripts\start_unreviewed_dev.py --port 8000
```

Launcher sets exact CAUSORA_DEV_UNREVIEWED_MODE=UNREVIEWED_DEV_ONLY (not true/1/default), clears review/policy/release environment variables, isolates artifacts/traces/unreviewed-development/, and listens at 0.0.0.0:8000 by default. Use --host 127.0.0.1 for local-only.

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/api/simulate \
  -H 'Content-Type: application/json' \
  --data @examples/simulate_request_v1.json
```

| Location | Required marker |
| --- | --- |
| data.executionContext.mode | unreviewed_development_only |
| data.executionContext.decisionReady | false |
| data.executionContext.banner | UNREVIEWED — DEVELOPMENT ONLY... |
| data.simulation.dataVersion | Includes UNREVIEWED_DEV_ONLY |
| Every trace.runIdentity.executionMode | unreviewed_development_only |
| Contract parameter provenance | unreviewed_development_contract |
| Policy parameter provenance | unreviewed_development_assumption |
| X-Causora-Review-Status | unreviewed-development-only |
| X-Causora-Execution-Mode | unreviewed-development-only |

Selections are complete shape fields for Matrix/Trace development, not recommendations or approved Boardroom input.

To restore formal mode, stop launcher and use `uvicorn app.service:app --host 0.0.0.0 --port 8000`. Without exact opt-in, default remains v1 503 until authentic reviewed bundle, policy and release all validate.
