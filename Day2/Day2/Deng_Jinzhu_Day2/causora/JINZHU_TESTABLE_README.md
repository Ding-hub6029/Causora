# Deng Jinzhu Day 1 + Day 2: Testable Package

This package contains Deng's two Python modules and Ding's byte-identical synthetic test fixtures. It is not a standalone frontend, Wang review tool or completed team integration. To fix missing-file errors, `golden/` and `public/demo/` accompany `lib/` and `demo_data/` because tests read them.

| Directory | Ownership / use | Files |
| --- | --- | ---: |
| `simulation_day1/` | Deng's original manifest, v1 DTO mirrors, independent oracle and tests | 33 |
| `simulation_day2/` | Deng's 104-week deterministic engine, P2 lineage gate, boundary and tests | 23 |
| `lib/` | Ding's original contracts.ts, types.ts, metrics.ts, validation.ts for cross-language checks | 4 |
| `demo_data/` | Ding's original mock and synthetic notice CSV | 2 |
| `golden/` | Ding's original Golden shape fixture | 1 |
| `public/demo/` | Ding's original demand, deliveries, inventory, notice and agreement fixtures | 5 |
| `API_CONTRACT.md` | Ding's shared original, read-only | 1 |

`JINZHU_TESTABLE_MANIFEST.sha256` records sources and fixtures. Those four fixture directories matched the supplied Ding Day 2 package byte for byte before English documentation localization. They are attributed to Ding, not Deng. No `app/`, `components/`, `evidence_day2/` or `causora_day1/` implementation is included. No integration/deployment is performed. Frozen Day 1 manifest and raw CSV remain matched; sources cannot be silently replaced.

## Windows CMD

Run from the extracted `causora/` directory containing all six peer directories:

```bat
cd /d "C:\your-path\causora"
dir simulation_day1\wire_models.py
dir simulation_day2\deterministic.py
dir lib\contracts.ts
dir demo_data\causora_day1_mock.json
py -3.12 -m pip install -r simulation_day1\requirements-test.txt "pytest>=8,<10"
py -3.12 -m pytest -q simulation_day1\tests simulation_day2\tests
```

If unavailable, replace `py -3.12` with the same `python` for installation and execution. PowerShell uses `Set-Location 'C:\your-path\causora'`. `simulation_day1` is a valid namespace package without `__init__.py`; check `wire_models.py`. Do not run from the tests subdirectory.

Historical fresh Linux extraction: 37 passed, 25 subtests (Day 1:16; Day 2:21); missing-module/file errors resolved. Windows-host testing was not performed for that delivery. Original Day 1 schema generation leaves a read-only XLSX resource unclosed and may warn with strict `-W error`; its source is bound to Wang's scope and was not silently changed. The standard commands do not enable `-W error`. Fixes affecting that scope require coordinated version/review updates. Eleven review items were pending at Day 2; model inputs remained unapproved. Passing tests does not release official probability/P90 or recommendations.
