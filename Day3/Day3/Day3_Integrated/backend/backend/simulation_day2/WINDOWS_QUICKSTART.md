# Windows: Deng Day 1/Day 2 Test Package

Contains Deng's simulation_day1/simulation_day2 and Ding's original lib/demo_data/golden/public/demo fixtures. No frontend, Wang implementation or approved inputs. Not team integration. See [inventory](../JINZHU_TESTABLE_README.md).

From extracted `causora/`, not a ZIP preview or tests subdirectory:

```bat
cd /d "C:\your-path\causora"
dir simulation_day1\wire_models.py
dir simulation_day2\deterministic.py
dir lib\contracts.ts
dir demo_data\causora_day1_mock.json
dir golden\golden_run.json
dir public\demo\historical_demand.csv
py -3.12 -m pip install -r simulation_day1\requirements-test.txt "pytest>=8,<10"
py -3.12 -m pytest -q simulation_day1\tests simulation_day2\tests
```

PowerShell: replace cd /d with `Set-Location 'C:\your-path\causora'`. If needed, replace py -3.12 with the same python for install/run. simulation_day1 is a namespace package. Absent __init__.py is valid. python -m pytest adds current directory to imports.

Historical fresh Linux extraction: 37 passed, 25 subtests. No actual Windows host test for that delivery. Regression success is not review or approval.
