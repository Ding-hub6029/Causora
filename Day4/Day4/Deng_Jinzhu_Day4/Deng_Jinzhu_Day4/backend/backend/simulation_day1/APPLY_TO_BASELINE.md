# Apply to the Shared Baseline

This add-on contains only `causora/simulation_day1/`. Extract the baseline `Causora-Day1-Delivery-v4.1(1).zip` first, then overlay this add-on at its parent directory. Do not overwrite `API_CONTRACT.md`, `lib/contracts.ts`, `lib/types.ts`, mock JSON or Golden.

From `causora/`:

```bash
python3 -m pip install -r simulation_day1/requirements-test.txt
python3 -m simulation_day1.build_day1_schemas
python3 -m simulation_day1.interfaces
python3 -m unittest discover -s simulation_day1/tests -v
```

On Windows use the same available `py`/`python` interpreter for installation and execution. JSON reads explicitly use UTF-8. Non-UTF-8 default testing passed. Verify the target Windows host too.

Read section 4 of [handoff](DAY1_HANDOFF.md). The three owners must agree before shared baseline changes. `demo_inputs_v1.json` is an internal synthetic manifest, not a dataset API payload. Generated schemas mirror v1, not replacements for TS contracts. LOCAL_MOCK examples run without a server and are not real results. Only frozen scenarios/options are accepted. Risk/budget can rescreen the fixed cells.
