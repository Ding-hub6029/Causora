# Unreviewed Day 3 data package — source compatibility

This package contains **calculation data only**. It remains:

- `UNREVIEWED_SYNTHETIC_TEST_ONLY_NO_PUBLIC_SUCCESS`;
- `PENDING_11_HUMAN_REVIEW_ROWS`;
- `UNAPPROVED_TEST_INPUT`.

It is not a `/api/simulate` response, reviewed bundle, policy approval, v2 release or Boardroom input.

## Reproduction source

Use this same unified package's `../backend/` directory and run from that directory:

```bash
source .venv/bin/activate
python scripts/reproduce_deng_day3_data.py \
  --out /tmp/day3-reproduced \
  --expected-manifest ../data/deng_day3_data_manifest.json
```

Expected engine source hashes:

| Engine source | SHA-256 |
| --- | --- |
| `simulation_day3/monte_carlo.py` | `daaaf84bb5abeeff7b89413ee9d0d5e4d6fd7e8da48bd1985daf360eac755da8` |
| `simulation_day3/models.py` | `26504bc029e704fc125e6afb57bc6592f2caf111ea54ba4e05a81e9df462b5ca` |
| `simulation_day3/policy.py` | `0dd84f4f390254a5897f73c6e96a9db54650b295d32ca8a85c9d0bc536dc9d47` |

With the same request, policy and seed `1042026`, the reproduction check verifies the same `previewId` and all three original data JSON SHA-256 values. The unified backend changes interface/release/verifier/development-entry code only; it does not change these engine files.
