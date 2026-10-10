# LLM + Local-Code Shared-Control Prompt

Use only the supplied frozen **shared control input**. You may write a small, self-contained arithmetic program, but you must not import Causora source code, read repository files, browse, call external tools, or call an API. The expected labels are deliberately not supplied.

Return strict JSON with this result-only shape:

```json
{
  "method": "llm_plus_code",
  "oracleCaseResults": [
    {
      "caseId": "exact-shared-case-id",
      "answer": {},
      "evidenceRefs": ["control:exact-shared-case-id"],
      "poisonPillFlags": ["recognized-rule-or-trap-id"],
      "codeSummary": "brief algorithm summary",
      "codeArtifactSha256": "64-char SHA-256 of the actually executed self-contained code"
    }
  ],
  "notes": "short explanation of any uncertainty"
}
```

Return every supplied case exactly once; do not add a case. The operator must separately retain the code artifact and redacted execution log, record their SHA-256 values in the capture reproducibility block, and validate the capture before import. A declaration that code was used is not execution evidence.

Rules: half-even whole-USD rounding; nearest-rank P90 `ceil(0.90 × N)` after sorting; revenue zero produces a null gross margin and `INVALID_REVENUE_ZERO`; a selected option must pass feasibility, stockout threshold, and cash ceiling. Identify applicable poison pills, including no divide-by-one, no P90 interpolation, and no recommendation for no-feasible cases. This is an evaluation control, never an approval or external action request.
