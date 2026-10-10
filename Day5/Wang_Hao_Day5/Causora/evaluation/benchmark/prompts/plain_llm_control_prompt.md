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
