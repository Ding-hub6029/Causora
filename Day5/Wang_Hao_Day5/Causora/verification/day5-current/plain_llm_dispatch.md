# Plain LLM Shared-Control Prompt

Use only the supplied frozen **shared control input**. Do not browse, call tools, access files, or infer missing facts. The expected labels are deliberately not supplied. For each case, calculate the requested displayed cost components, TCO, revenue state, P90, or selected option using the stated rules.

Return strict JSON with this result-only shape:

```json
{
  "method": "plain_llm",
  "oracleCaseResults": [
    {
      "caseId": "exact-shared-case-id",
      "answer": {},
      "evidenceRefs": ["control:exact-shared-case-id"],
      "poisonPillFlags": ["recognized-rule-or-trap-id"]
    }
  ],
  "notes": "short explanation of any uncertainty"
}
```

Return every supplied case exactly once; do not add a case. `evidenceRefs` must cite the supplied `control:<caseId>` reference for that case. Identify applicable traps: half-even whole-USD rounding, locked renewal premium, locked termination fee, no divide-by-one for zero revenue, nearest-rank rather than interpolation, simultaneous risk/cash constraints, and no recommendation when no option is feasible.

Rules: use half-even rounding for whole USD; P90 is `ceil(0.90 × N)` on sorted values; when revenue is zero, gross margin is `null` and the status is `INVALID_REVENUE_ZERO`; a recommendation exists only when feasible, stockout probability is at or below the threshold, and P90 cash is at or below the ceiling.

This prompt is an evaluation control. It is not a procurement, legal, financial, or approval instruction.

## Frozen shared input supplied to the evaluated method

Do not request or infer an answer key. Return results only for these cases.

```json
{
  "schema": "causora.day5-benchmark-shared-inputs.v1",
  "purpose": "The same answer-free controls must be supplied to Causora, plain LLM, and LLM plus local code. Expected labels are stored separately and must never be sent in an evaluation prompt.",
  "source": "DAY5_SHARED_SYNTHETIC_CONTROL_INPUTS_PENDING_HUMAN_REVIEW_RECORD",
  "rules": [
    "Round displayed whole USD with half-even rounding.",
    "P90 uses nearest rank ceil(0.90 × N) on sorted actual cash values.",
    "Revenue zero yields null gross margin and INVALID_REVENUE_ZERO; do not divide by one.",
    "A selected option must be feasible and pass both the stockout threshold and cash ceiling."
  ],
  "cases": [
    {
      "caseId": "locked_mixed_cost_rounding",
      "kind": "cost",
      "evidenceRef": "control:locked_mixed_cost_rounding",
      "input": {
        "unitsFromA": 150,
        "unitsFromB": 100,
        "priceAUsd": "12.00",
        "priceBUsd": "12.60",
        "renewalLocked": true,
        "renewalUpliftFraction": "0.14",
        "terminateA": false,
        "terminationFeeUsd": 25000,
        "rawHoldingMeanUsd": "25.5",
        "rawStockoutLossMeanUsd": "5.5",
        "fulfilledUnits": 250,
        "sellingPriceUsdPerUnit": "20.00"
      }
    },
    {
      "caseId": "locked_exit_fee_and_half_even",
      "kind": "cost",
      "evidenceRef": "control:locked_exit_fee_and_half_even",
      "input": {
        "unitsFromA": 0,
        "unitsFromB": 250,
        "priceAUsd": "12.00",
        "priceBUsd": "12.60",
        "renewalLocked": true,
        "renewalUpliftFraction": "0.14",
        "terminateA": true,
        "terminationFeeUsd": 25000,
        "rawHoldingMeanUsd": "0.5",
        "rawStockoutLossMeanUsd": "1.5",
        "fulfilledUnits": 250,
        "sellingPriceUsdPerUnit": "20.00"
      }
    },
    {
      "caseId": "zero_revenue_is_invalid_not_divided_by_one",
      "kind": "cost",
      "evidenceRef": "control:zero_revenue_is_invalid_not_divided_by_one",
      "input": {
        "unitsFromA": 0,
        "unitsFromB": 0,
        "priceAUsd": "12.00",
        "priceBUsd": "12.60",
        "renewalLocked": false,
        "renewalUpliftFraction": "0.14",
        "terminateA": false,
        "terminationFeeUsd": 25000,
        "rawHoldingMeanUsd": "0",
        "rawStockoutLossMeanUsd": "0",
        "fulfilledUnits": 0,
        "sellingPriceUsdPerUnit": "20.00"
      }
    },
    {
      "caseId": "p90_nearest_rank_ten_trials",
      "kind": "p90",
      "evidenceRef": "control:p90_nearest_rank_ten_trials",
      "input": {
        "cashOutflowUsd": [
          6,
          12,
          25,
          9,
          50,
          45,
          18,
          23,
          36,
          31
        ]
      }
    },
    {
      "caseId": "constraint_selection_and_order",
      "kind": "selection",
      "evidenceRef": "control:constraint_selection_and_order",
      "input": {
        "riskThreshold": "0.12",
        "budgetCeilingUsd": 480,
        "options": [
          {
            "optionId": "D0",
            "feasible": true,
            "stockoutProbability": "0.20",
            "cashOutflowP90": 300,
            "expectedTco": 300
          },
          {
            "optionId": "D1",
            "feasible": true,
            "stockoutProbability": "0.05",
            "cashOutflowP90": 310,
            "expectedTco": 310
          },
          {
            "optionId": "D2",
            "feasible": true,
            "stockoutProbability": "0.05",
            "cashOutflowP90": 550,
            "expectedTco": 280
          }
        ]
      }
    },
    {
      "caseId": "no_feasible_option_is_explicit",
      "kind": "selection",
      "evidenceRef": "control:no_feasible_option_is_explicit",
      "input": {
        "riskThreshold": "0.12",
        "budgetCeilingUsd": 480,
        "options": [
          {
            "optionId": "D0",
            "feasible": false,
            "stockoutProbability": "0.20",
            "cashOutflowP90": 500,
            "expectedTco": 300
          },
          {
            "optionId": "D1",
            "feasible": true,
            "stockoutProbability": "0.13",
            "cashOutflowP90": 310,
            "expectedTco": 310
          },
          {
            "optionId": "D2",
            "feasible": true,
            "stockoutProbability": "0.05",
            "cashOutflowP90": 550,
            "expectedTco": 280
          }
        ]
      }
    }
  ]
}
```

## Run identity supplied by the operator

{
  "method": "plain_llm",
  "commonInputSha256": "12ccc54cc4fd6ed6e38848b38d5f44fc6996a0807f6fc64f574a46c6322c82a8",
  "promptSha256": "ac6c9b5eac1b17d8fd969ae1fc9cbc04a6fc01b81eda10ddff4ed07a820c9a0c",
  "expectedResultCaseIds": [
    "locked_mixed_cost_rounding",
    "locked_exit_fee_and_half_even",
    "zero_revenue_is_invalid_not_divided_by_one",
    "p90_nearest_rank_ten_trials",
    "constraint_selection_and_order",
    "no_feasible_option_is_explicit"
  ]
}
