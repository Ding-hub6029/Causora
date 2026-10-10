import json
from decimal import Decimal, ROUND_HALF_EVEN

# Embedded frozen shared input
shared = {
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
        "renewalLocked": True,
        "renewalUpliftFraction": "0.14",
        "terminateA": False,
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
        "renewalLocked": True,
        "renewalUpliftFraction": "0.14",
        "terminateA": True,
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
        "renewalLocked": False,
        "renewalUpliftFraction": "0.14",
        "terminateA": False,
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
        "cashOutflowUsd": [6,12,25,9,50,45,18,23,36,31]
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
          {"optionId": "D0", "feasible": True, "stockoutProbability": "0.20", "cashOutflowP90": 300, "expectedTco": 300},
          {"optionId": "D1", "feasible": True, "stockoutProbability": "0.05", "cashOutflowP90": 310, "expectedTco": 310},
          {"optionId": "D2", "feasible": True, "stockoutProbability": "0.05", "cashOutflowP90": 550, "expectedTco": 280}
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
          {"optionId": "D0", "feasible": False, "stockoutProbability": "0.20", "cashOutflowP90": 500, "expectedTco": 300},
          {"optionId": "D1", "feasible": True, "stockoutProbability": "0.13", "cashOutflowP90": 310, "expectedTco": 310},
          {"optionId": "D2", "feasible": True, "stockoutProbability": "0.05", "cashOutflowP90": 550, "expectedTco": 280}
        ]
      }
    }
  ]
}

# Helper: half-even rounding to whole USD
def round_usd(value):
    d = Decimal(value)
    return int(d.quantize(Decimal('1'), rounding=ROUND_HALF_EVEN))

results = []

# Process cases
for c in shared['cases']:
    cid = c['caseId']
    if c['kind'] == 'cost':
        inp = c['input']
        a = Decimal(str(inp['unitsFromA'])) * Decimal(str(inp['priceAUsd']))
        b = Decimal(str(inp['unitsFromB'])) * Decimal(str(inp['priceBUsd']))
        procurement = a + b
        if inp.get('renewalLocked'):
            uplift = Decimal(str(inp.get('renewalUpliftFraction', '0')))
            procurement = procurement * (Decimal('1') + uplift)
        termination = Decimal(str(inp.get('terminationFeeUsd', 0))) if inp.get('terminateA') else Decimal('0')
        holding = Decimal(str(inp.get('rawHoldingMeanUsd', '0'))) * Decimal(str(inp.get('fulfilledUnits', 0)))
        total_units = int(inp.get('unitsFromA', 0)) + int(inp.get('unitsFromB', 0))
        unfulfilled = max(0, total_units - int(inp.get('fulfilledUnits', 0)))
        stockout = Decimal(str(inp.get('rawStockoutLossMeanUsd', '0'))) * Decimal(str(unfulfilled))
        total_cost = procurement + holding + stockout + termination
        revenue = Decimal(str(inp.get('sellingPriceUsdPerUnit', '0'))) * Decimal(str(inp.get('fulfilledUnits', 0)))
        # Apply rule: revenue zero => null gross margin and flag
        if revenue == 0:
            gross_margin_usd = None
            gross_margin_pct = None
            poison = ["recognized-rule-or-trap-id", "INVALID_REVENUE_ZERO"]
        else:
            gm = revenue - total_cost
            gross_margin_usd = int(Decimal(gm).quantize(Decimal('1'), rounding=ROUND_HALF_EVEN))
            # percentage with two decimals
            gross_margin_pct = float((gm / revenue * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN))
            poison = ["recognized-rule-or-trap-id"]
        entry = {
            'caseId': cid,
            'answer': {
                'procurementCostUsd': round_usd(procurement),
                'holdingCostUsd': round_usd(holding),
                'stockoutCostUsd': round_usd(stockout),
                'terminationFeeUsd': round_usd(termination),
                'totalCostUsd': round_usd(total_cost),
                'revenueUsd': round_usd(revenue),
                'grossMarginUsd': gross_margin_usd,
                'grossMarginPct': gross_margin_pct
            },
            'evidenceRefs': [c['evidenceRef']],
            'poisonPillFlags': poison,
            'codeSummary': 'Compute procurement (units×price), apply uplift if locked, add holding/stockout/termination, compute revenue; round USD half-even to whole dollars.',
            'codeArtifactSha256': '0000000000000000000000000000000000000000000000000000000000000000'
        }
        results.append(entry)
    elif c['kind'] == 'p90':
        vals = list(c['input']['cashOutflowUsd'])
        sorted_vals = sorted(vals)
        n = len(sorted_vals)
        rank = int( (Decimal('0.9') * Decimal(n)).to_integral_value(rounding=ROUND_HALF_EVEN) )
        # nearest-rank uses ceil(0.90*N)
        import math
        rank = math.ceil(0.9 * n)
        p90 = sorted_vals[max(0, rank-1)]
        entry = {
            'caseId': cid,
            'answer': {
                'sortedCashOutflowsUsd': sorted_vals,
                'p90Usd': p90,
                'p90Method': 'nearest-rank-ceil(0.90*N)'
            },
            'evidenceRefs': [c['evidenceRef']],
            'poisonPillFlags': ['recognized-rule-or-trap-id', 'no_p90_interpolation'],
            'codeSummary': 'Sort cash outflows and select element at rank ceil(0.90*N) (no interpolation).',
            'codeArtifactSha256': '0000000000000000000000000000000000000000000000000000000000000000'
        }
        results.append(entry)
    elif c['kind'] == 'selection':
        inp = c['input']
        risk = Decimal(str(inp['riskThreshold']))
        budget = Decimal(str(inp['budgetCeilingUsd']))
        options = inp['options']
        passers = []
        for o in options:
            feasible = bool(o.get('feasible'))
            stockout = Decimal(str(o.get('stockoutProbability')))
            cash_p90 = Decimal(str(o.get('cashOutflowP90')))
            if feasible and stockout <= risk and cash_p90 <= budget:
                passers.append(o)
        selected = None
        if len(passers) == 0:
            poison = ['recognized-rule-or-trap-id', 'no_recommendation_for_no_feasible_cases']
            selected_id = None
            selection_reason = 'No option satisfied all constraints (feasibility, stockout threshold, and cash ceiling). No recommendation per rule.'
        else:
            # tie-break: pick lowest expectedTco
            passers_sorted = sorted(passers, key=lambda x: x.get('expectedTco', float('inf')))
            selected_id = passers_sorted[0]['optionId']
            poison = ['recognized-rule-or-trap-id']
            selection_reason = 'Feasible and passed both stockout threshold and cash ceiling; chosen among passers by lowest expected TCO when multiple.'
        entry = {
            'caseId': cid,
            'answer': {
                'budgetCeilingUsd': int(budget),
                'riskThreshold': float(risk),
                'optionsPassed': passers,
                'selectedOptionId': selected_id,
                'selectionReason': selection_reason
            },
            'evidenceRefs': [c['evidenceRef']],
            'poisonPillFlags': poison,
            'codeSummary': 'Filter options by feasibility, stockout <= risk threshold, and cashOutflowP90 <= budget; select lowest expectedTco among passers.',
            'codeArtifactSha256': '0000000000000000000000000000000000000000000000000000000000000000'
        }
        results.append(entry)

output = {
    'method': 'llm_plus_code',
    'oracleCaseResults': results,
    'notes': 'Assumptions for cost formulae documented in codeSummary where needed.'
}

print(json.dumps(output, separators=(',', ':'), ensure_ascii=False))
