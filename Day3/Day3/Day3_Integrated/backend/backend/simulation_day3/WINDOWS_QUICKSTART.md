# Deng Day 3 Windows Quick Start (Historical Owner Package)

Extract the original testable package and enter causora/, with peer simulation_day1/2/3 and original lib/demo_data/golden/public/demo fixtures. Do not run pytest from the ZIP's parent. For the current integrated backend, enter backend/backend/ and follow RUNBOOK.md.

```powershell
cd C:\your-path\causora
py -3.12 -m pip install -r simulation_day1/requirements-test.txt -r simulation_day3/requirements-test.txt
py -3.12 -m pytest -q simulation_day1/tests simulation_day2/tests simulation_day3/tests
```

If python --version is 3.12 and py unavailable, use the same python for both install/test. NumPy 2.5.3 pins exact PCG64 replay. Run python -m pytest -q simulation_day3/tests only from causora/.

For a new unapproved 1000-run internal output, consult `python -m simulation_day3.cli --help` and choose a nonexistent UNAPPROVED filename. CLI refuses overwrite. This output is not frontend POST/api/simulate200. At original delivery missing Wang review/policy meant v1 503 only. Historical fresh Linux extraction passed. Original Windows host was not tested. Later actual Windows checks/current service are documented in the integrated technical report.

```bat
py -3.12 -m simulation_day3.cli preview --project-root . --request simulation_day1\examples\simulate_request.json --policy simulation_day3\examples\UNAPPROVED_MC_POLICY.json --out simulation_day3\examples\my_run_UNAPPROVED.json
```
