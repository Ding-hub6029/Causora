# Deng Day 3 data-package source correlation

## Correction to the standalone data delivery

The JSON-only data package was created from the source snapshot in **this directory**. It omitted that source snapshot, which made its `previewId` and engine hashes impossible to independently replay from the earlier v7 archive. This document fixes the linkage.

| Source file | SHA-256 recorded inside the delivered data | v7 SHA-256 | Why it changed |
| --- | --- | --- | --- |
| `simulation_day3/monte_carlo.py` | `daaaf84bb5abeeff7b89413ee9d0d5e4d6fd7e8da48bd1985daf360eac755da8` | `3007863a5546221a0cde9996927d88e6769257b7f4d865b59b0f9c5e21323649` | Appended the separately gated `run_reviewed_monte_carlo` path after the existing `run_unapproved_monte_carlo` function. The internal unapproved calculation loop was not changed. Because `previewId` fingerprints source hashes, the identifier changed. |
| `simulation_day3/models.py` | `26504bc029e704fc125e6afb57bc6592f2caf111ea54ba4e05a81e9df462b5ca` | same | No change. |
| `simulation_day3/policy.py` | `0dd84f4f390254a5897f73c6e96a9db54650b295d32ca8a85c9d0bc536dc9d47` | `bea197fac7fc57ee93338ea5597bae96b8c3d9be9536a2cd582f985e918abc9c` | Added a distinct `TEAM_APPROVED` policy state and a matching provenance check for the future reviewed route. The supplied data uses `UNAPPROVED_TEST_INPUT` exactly as before. |

The previous data package has:

- `previewId`: `mc-preview-23b1fb68e27d2cce45fb`
- seed: `1042026`
- 1,000 Monte Carlo runs × 104 weeks
- source dataset: `demo-2026.10.04-v4`
- data status: `UNREVIEWED_SYNTHETIC_TEST_ONLY_NO_PUBLIC_SUCCESS`

## Independent reproduction

```bash
cd Causora-Day3-Backend-Gated
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/reproduce_deng_day3_data.py \
  --out /tmp/deng-day3-reproduced \
  --expected-manifest /path/to/deng_day3_data_manifest.json
```

Expected terminal result:

```text
REPRODUCTION_PASS: previewId and all three delivered data-file SHA-256 values match.
```

The script first refuses to run if the three recorded engine source hashes do not match. It then regenerates all three JSON data files and compares each SHA-256 plus `previewId`. It writes **UTF-8 without BOM and LF-only JSON bytes**, preventing Windows `CRLF` conversion from changing the hashes. It reproduces the data only; it does not assert a human review, decision approval or HTTP API success. See `WINDOWS_ENCODING_AND_REPRODUCTION.md`.

## Service link

The same source tree contains the runnable FastAPI service and its v2 Matrix + Trace success builder. The service has a valid 200 code path, but default startup correctly returns 503 pending-review responses because no Wang review bundle, approved policy verifier or v2 release verifier is included in this delivery. See [`contracts/TRACE_CONTRACT_V2_RELEASE_VERIFIER.md`](contracts/TRACE_CONTRACT_V2_RELEASE_VERIFIER.md).
