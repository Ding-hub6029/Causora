// Generated from actual artifacts; checked against the unchanged Ding Day3 contract.
import type { SimulationResult, Scenario, DecisionOption, DatasetResult, AgentOutput } from "../reference/contracts";
export const simulation = {
  "simulationId": "sim-day1-mock-0001",
  "seed": 1042026,
  "dataVersion": "demo-2026.10.04-v4",
  "formulaVersion": "tco-v1",
  "weeks": 104,
  "monteCarloRuns": 0,
  "matrix": {
    "baseline": [
      {
        "optionId": "D0",
        "feasible": true,
        "expectedTco": 420000,
        "stockoutProbability": 0.09,
        "serviceLevel": 0.968,
        "cashOutflowP90": 451000,
        "breakdown": {
          "purchase": 312000,
          "holding": 38000,
          "stockoutLoss": 26320,
          "renewalPremium": 43680,
          "terminationFee": 0
        },
        "unitsFromA": 26000,
        "unitsFromB": 0,
        "tone": "neutral"
      },
      {
        "optionId": "D1",
        "feasible": true,
        "expectedTco": 411000,
        "stockoutProbability": 0.05,
        "serviceLevel": 0.981,
        "cashOutflowP90": 430000,
        "breakdown": {
          "purchase": 318240,
          "holding": 41500,
          "stockoutLoss": 25052,
          "renewalPremium": 26208,
          "terminationFee": 0
        },
        "unitsFromA": 15600,
        "unitsFromB": 10400,
        "tone": "recommended"
      },
      {
        "optionId": "D2",
        "feasible": true,
        "expectedTco": 445000,
        "stockoutProbability": 0.03,
        "serviceLevel": 0.988,
        "cashOutflowP90": 471000,
        "breakdown": {
          "purchase": 327600,
          "holding": 44000,
          "stockoutLoss": 48400,
          "renewalPremium": 0,
          "terminationFee": 25000
        },
        "unitsFromA": 0,
        "unitsFromB": 26000,
        "tone": "neutral"
      }
    ],
    "demand-drop": [
      {
        "optionId": "D0",
        "feasible": true,
        "expectedTco": 438000,
        "stockoutProbability": 0.13,
        "serviceLevel": 0.957,
        "cashOutflowP90": 476000,
        "breakdown": {
          "purchase": 294000,
          "holding": 76000,
          "stockoutLoss": 26840,
          "renewalPremium": 41160,
          "terminationFee": 0
        },
        "unitsFromA": 24500,
        "unitsFromB": 0,
        "tone": "risk"
      },
      {
        "optionId": "D1",
        "feasible": true,
        "expectedTco": 419000,
        "stockoutProbability": 0.07,
        "serviceLevel": 0.977,
        "cashOutflowP90": 444000,
        "breakdown": {
          "purchase": 318240,
          "holding": 48000,
          "stockoutLoss": 26552,
          "renewalPremium": 26208,
          "terminationFee": 0
        },
        "unitsFromA": 15600,
        "unitsFromB": 10400,
        "tone": "recommended"
      },
      {
        "optionId": "D2",
        "feasible": true,
        "expectedTco": 452000,
        "stockoutProbability": 0.04,
        "serviceLevel": 0.983,
        "cashOutflowP90": 482000,
        "breakdown": {
          "purchase": 309960,
          "holding": 90000,
          "stockoutLoss": 27040,
          "renewalPremium": 0,
          "terminationFee": 25000
        },
        "unitsFromA": 0,
        "unitsFromB": 24600,
        "tone": "neutral"
      }
    ],
    "lead-stress": [
      {
        "optionId": "D0",
        "feasible": true,
        "expectedTco": 451000,
        "stockoutProbability": 0.2,
        "serviceLevel": 0.924,
        "cashOutflowP90": 489000,
        "breakdown": {
          "purchase": 312000,
          "holding": 40000,
          "stockoutLoss": 55320,
          "renewalPremium": 43680,
          "terminationFee": 0
        },
        "unitsFromA": 26000,
        "unitsFromB": 0,
        "tone": "risk"
      },
      {
        "optionId": "D1",
        "feasible": true,
        "expectedTco": 430000,
        "stockoutProbability": 0.1,
        "serviceLevel": 0.966,
        "cashOutflowP90": 455000,
        "breakdown": {
          "purchase": 318240,
          "holding": 43500,
          "stockoutLoss": 42052,
          "renewalPremium": 26208,
          "terminationFee": 0
        },
        "unitsFromA": 15600,
        "unitsFromB": 10400,
        "tone": "recommended"
      },
      {
        "optionId": "D2",
        "feasible": true,
        "expectedTco": 463000,
        "stockoutProbability": 0.06,
        "serviceLevel": 0.979,
        "cashOutflowP90": 497000,
        "breakdown": {
          "purchase": 327600,
          "holding": 46000,
          "stockoutLoss": 64400,
          "renewalPremium": 0,
          "terminationFee": 25000
        },
        "unitsFromA": 0,
        "unitsFromB": 26000,
        "tone": "neutral"
      }
    ]
  },
  "unitPricesUsd": {
    "A": 12.0,
    "B": 12.6
  }
} satisfies SimulationResult;
export const scenarios = [
  {
    "id": "baseline",
    "label": "Baseline",
    "tag": "Reference case",
    "demandShock": 0,
    "demandUnits24m": 26000,
    "leadTime": "Normal",
    "leadTimeMultiplier": 1.0,
    "description": "Expected demand and normal supplier lead-time variability."
  },
  {
    "id": "demand-drop",
    "label": "Demand −15%",
    "tag": "Cash stress",
    "demandShock": -15,
    "demandUnits24m": 22100,
    "leadTime": "Normal",
    "leadTimeMultiplier": 1.0,
    "description": "Demand contracts while the minimum purchase commitment remains active."
  },
  {
    "id": "lead-stress",
    "label": "Lead-time stress",
    "tag": "Service risk",
    "demandShock": 0,
    "demandUnits24m": 26000,
    "leadTime": "+30% variability",
    "leadTimeMultiplier": 1.3,
    "description": "Supplier A delivery variability rises under logistics pressure."
  }
] satisfies Scenario[];
export const options = [
  {
    "id": "D0",
    "label": "Keep A",
    "shareA": 1.0,
    "terminateA": false,
    "allocation": "100% A · 0% B",
    "short": "100% A",
    "description": "Preserve the current supplier allocation."
  },
  {
    "id": "D1",
    "label": "Minimum A + Diversify B",
    "shareA": 0.6,
    "terminateA": false,
    "allocation": "60% A · 40% B",
    "short": "60% A / 40% B",
    "description": "Respect the locked minimum while reducing concentration."
  },
  {
    "id": "D2",
    "label": "Exit A + Move to B",
    "shareA": 0.0,
    "terminateA": true,
    "allocation": "0% A · 100% B",
    "short": "Exit A / 100% B",
    "description": "Exit the renewed agreement and include the contract fee."
  }
] satisfies DecisionOption[];
export const contractInputs = {
  "contract": {
    "decisionDate": "2026-10-04",
    "renewalDate": "2026-11-18",
    "daysToRenewal": 45,
    "renewalNoticeDays": 60,
    "noticeDeadline": "2026-09-19",
    "noticeSent": false,
    "noticeRecordSource": "supplier_correspondence_log.csv — no written notice entry before 2026-09-19 (mock input)",
    "renewalLocked": true,
    "renewalTermMonths": 24,
    "renewalPriceIncreasePct": 0.14,
    "minPurchaseShareA": 0.6,
    "forecastBasis": "locked-at-renewal",
    "lockedForecastUnits24m": 26000,
    "minPurchaseUnitsA": 15600,
    "terminationFeeUsd": 25000,
    "evidenceIds": [
      "EV-014",
      "EV-019",
      "EV-021",
      "EV-024",
      "EV-027"
    ]
  },
  "evidence": [
    {
      "id": "EV-014",
      "sourceFile": "supplier_a_agreement.pdf",
      "page": 4,
      "quote": "If written notice is not received at least 60 days before renewal, the agreement automatically renews.",
      "locatorBbox": [
        54.0,
        170.1750030517578,
        543.7199096679688,
        185.28900146484375
      ],
      "extractedField": "renewal_notice_days",
      "extractedValue": "60 days",
      "matchMethod": "exact",
      "matchScore": 1.0,
      "quoteMatched": true
    },
    {
      "id": "EV-019",
      "sourceFile": "supplier_a_agreement.pdf",
      "page": 4,
      "quote": "The agreement automatically renews for 24 months at a 14% higher unit price.",
      "locatorBbox": [
        54.0,
        198.1750030517578,
        435.5019836425781,
        213.28900146484375
      ],
      "extractedField": "renewal_term_months",
      "extractedValue": "24 months",
      "matchMethod": "exact",
      "matchScore": 1.0,
      "quoteMatched": true
    },
    {
      "id": "EV-021",
      "sourceFile": "supplier_a_agreement.pdf",
      "page": 4,
      "quote": "The agreement automatically renews for 24 months at a 14% higher unit price.",
      "locatorBbox": [
        54.0,
        198.1750030517578,
        435.5019836425781,
        213.28900146484375
      ],
      "extractedField": "renewal_price_increase_pct",
      "extractedValue": "14%",
      "matchMethod": "exact",
      "matchScore": 1.0,
      "quoteMatched": true
    },
    {
      "id": "EV-024",
      "sourceFile": "supplier_a_agreement.pdf",
      "page": 4,
      "quote": "The renewed term has a minimum purchase commitment equal to 60% of forecast demand.",
      "locatorBbox": [
        54.0,
        226.1750030517578,
        499.676025390625,
        241.28900146484375
      ],
      "extractedField": "min_purchase_share_A",
      "extractedValue": "60%",
      "matchMethod": "exact",
      "matchScore": 1.0,
      "quoteMatched": true
    },
    {
      "id": "EV-027",
      "sourceFile": "supplier_a_agreement.pdf",
      "page": 4,
      "quote": "Early exit during the renewed term incurs a fixed termination fee of $25,000.",
      "locatorBbox": [
        54.0,
        254.1750030517578,
        423.2809753417969,
        269.28900146484375
      ],
      "extractedField": "termination_fee",
      "extractedValue": "$25,000",
      "matchMethod": "exact",
      "matchScore": 1.0,
      "quoteMatched": true
    }
  ],
  "variables": [
    {
      "key": "renewal_locked",
      "name": "Renewal locked-in",
      "value": "Yes",
      "unit": "boolean",
      "source": "EV-014",
      "meaning": "The notice deadline passed with no written notice on record, so the agreement renews.",
      "inputs": [
        {
          "name": "decision_date",
          "value": "2026-10-04",
          "source": "contract.decisionDate"
        },
        {
          "name": "renewal_date",
          "value": "2026-11-18",
          "source": "contract.renewalDate"
        },
        {
          "name": "days_to_renewal",
          "value": "45 days",
          "source": "derived"
        },
        {
          "name": "renewal_notice_days",
          "value": "60 days",
          "source": "EV-014"
        },
        {
          "name": "notice_sent_before_deadline",
          "value": "No",
          "source": "contract.noticeRecordSource"
        }
      ]
    },
    {
      "key": "renewal_term_months",
      "name": "Renewal term",
      "value": "24 months",
      "unit": "months",
      "source": "EV-019",
      "meaning": "The price uplift and the minimum commitment persist for the whole simulated horizon.",
      "inputs": [
        {
          "name": "renewal_term_months",
          "value": "24",
          "source": "EV-019"
        },
        {
          "name": "simulation_weeks",
          "value": "104",
          "source": "simulation.weeks"
        }
      ]
    },
    {
      "key": "effective_price_A",
      "name": "Effective price A",
      "value": "Base × 1.14",
      "unit": "USD per unit",
      "source": "EV-021",
      "meaning": "Purchase cost is booked at base price; the {{evidence:EV-021}} uplift is reported separately as renewal premium.",
      "inputs": [
        {
          "name": "base_price_A",
          "value": "$12.00",
          "source": "supplier_delivery_history.xlsx"
        },
        {
          "name": "renewal_price_increase_pct",
          "value": "14%",
          "source": "EV-021"
        }
      ]
    },
    {
      "key": "min_purchase_share_A",
      "name": "Minimum share A",
      "value": "60% of locked forecast",
      "unit": "share",
      "source": "EV-024",
      "meaning": "{{contract:minPurchaseUnitsA}} must still be bought from A even if demand falls; D1 stays feasible, D2 pays the exit fee.",
      "inputs": [
        {
          "name": "min_purchase_share_A",
          "value": "60%",
          "source": "EV-024"
        },
        {
          "name": "forecast_basis",
          "value": "locked at renewal",
          "source": "contract.forecastBasis"
        },
        {
          "name": "locked_forecast_units_24m",
          "value": "26,000 units",
          "source": "synthetic renewal-cycle forecast assumption; supplier_a_agreement.pdf p. 4 (not a sum of historical demand)"
        }
      ]
    },
    {
      "key": "termination_fee",
      "name": "Exit cost",
      "value": "$25,000",
      "unit": "USD",
      "source": "EV-027",
      "meaning": "Charged once when the renewed agreement is terminated (D2 only).",
      "inputs": [
        {
          "name": "termination_fee",
          "value": "$25,000",
          "source": "EV-027"
        },
        {
          "name": "renewal_locked",
          "value": "Yes",
          "source": "variables.renewal_locked"
        }
      ]
    }
  ]
} satisfies Pick<DatasetResult, "contract" | "evidence" | "variables">;
export const agentOutputs = [
  {
    "role": "CFO",
    "accent": "cobalt",
    "focus": "Financial exposure",
    "headline": "Financial tradeoffs need review",
    "body": "This synthetic illustration points to a tradeoff; inspect the referenced fields before deciding.",
    "metrics": [
      "expectedTcoUsd:D0",
      "cashOutflowP90Usd:D0"
    ],
    "status": "Watch"
  },
  {
    "role": "COO",
    "accent": "aqua",
    "focus": "Service continuity",
    "headline": "Service continuity needs review",
    "body": "This synthetic illustration points to a tradeoff; inspect the referenced fields before deciding.",
    "metrics": [
      "stockoutProbability:D0",
      "serviceLevel:D0"
    ],
    "status": "Watch"
  },
  {
    "role": "Risk",
    "accent": "coral",
    "focus": "Contract downside",
    "headline": "Contract exposure needs review",
    "body": "This synthetic illustration points to a tradeoff; inspect the referenced fields before deciding.",
    "metrics": [
      "cashOutflowP90Usd:D0",
      "cashOutflowP90Usd:D1"
    ],
    "status": "Watch"
  }
] satisfies AgentOutput[];
