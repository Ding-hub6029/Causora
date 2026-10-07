# Final fields and confirmation summary for Deng, Ding and Wang

## Please confirm

1. Keep `POST /api/simulate` request as `causora.contract.v1`; v1 remains the only error/pending envelope.
2. Use `causora.contract.v2` only for reviewed HTTP 200 success, with required `data.simulation`, `data.deltas`, `data.selections`, `data.traces[scenarioId][optionId]`.
3. Require exactly nine traces, one for every scenario × D0/D1/D2 cell; do not add a GET-trace endpoint.
4. Accept the field-level source vs review-record separation and the raw-mean/displayed-value/difference audit for every cost component.
5. Confirm all model-policy topics in `MODEL_POLICY_CONFIRMATIONS.md` through the three-owner policy record.
6. Confirm that Boardroom will receive `simulationId` and `dataVersion` only from a validated v2 success response.

## No core engine rewrite

The validated 104-week Monte Carlo algorithm and its Day3 engine sources are unchanged. The implementation changes are confined to input/release verification, reviewed contract propagation, response DTO/Trace audit data, run identifiers, documentation and tests. The engine source SHA-256 values remain:

```text
monte_carlo.py  daaaf84bb5abeeff7b89413ee9d0d5e4d6fd7e8da48bd1985daf360eac755da8
models.py       26504bc029e704fc125e6afb57bc6592f2caf111ea54ba4e05a81e9df462b5ca
policy.py       0dd84f4f390254a5897f73c6e96a9db54650b295d32ca8a85c9d0bc536dc9d47
```

These match the separately delivered unreviewed data package. Any reviewed v2 test sample in this package is explicitly named `TEST_FIXTURE_ONLY` and is not a Wang-reviewed or production result.
