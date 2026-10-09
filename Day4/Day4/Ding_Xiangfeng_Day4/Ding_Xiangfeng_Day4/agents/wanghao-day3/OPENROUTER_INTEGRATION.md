# Historical component document

This incoming document is preserved as history and is superseded by the root README.md and DAY4_FINAL_ACCEPTANCE.md. Its original bytes are retained under provenance/historical-integrated-reports/.

---

# OpenRouter integration

Final-code fresh native Gemini workflow: PASS. Evidence: verification/wang_day4/codex_final_revision/final_accepted. GPT roles ran concurrently, then Gemini Critic and GPT Synthesizer. Strict local validation passed. Current simulation/traces and pending approval flags were preserved.

Server configuration:

```text
CAUSORA_AI_PROVIDER=openrouter
CAUSORA_PRIMARY_MODEL=openai/gpt-5-mini
CAUSORA_GEMINI_CRITIC_MODEL=google/gemini-3.1-pro-preview
CAUSORA_FALLBACK_CRITIC_MODEL=openai/gpt-5-mini
CAUSORA_AI_MAX_CALLS=6
CAUSORA_AI_PIPELINE_CALLS=6
CAUSORA_AI_RETRIES=0
CAUSORA_AI_TOTAL_TIMEOUT=40
CAUSORA_AI_STAGE_TIMEOUT=10
CAUSORA_CRITIC_TIMEOUT=15
```

Configure OPENROUTER_API_KEY securely on the backend. No key is shipped. Route: https://openrouter.ai/api/v1. GPT uses strict upstream JSON Schema. Gemini requests a JSON object with the complete schema in system instructions because its strict-schema transport rejected the actual request. Both paths still require strict local Pydantic, numeric, evidence, allocation and cash checks. Incomplete/contradictory output is rejected.

Remote remaining above USD one is valid. Each workflow has a finite shared six-call budget and zero automatic retries. Effective expense ceiling is min(authorized amount, actual available allowance) minus USD 0.05. Persistent portalocker transactions retain conservative unknown fees. Integrated dispatch also requires CAUSORA_OPENROUTER_PAID_AUTHORIZED=YES, OPENROUTER_SCOPED_KEY_CONFIRMED=YES and CAUSORA_OPENROUTER_BUDGET_JOURNAL set to a private persistent shared path. These variables do not grant human approval.

scripts/verify_day4_codex_final.py defaults to read-only metadata. Its paid authorization is already consumed. Historical budgets and authorizations remain evidence. COST_SUMMARY.json aggregates all manual Codex repair attempts under the user's explicit authorization: known response-reported costs USD 0.13571115, one failed diagnostic fee unknown, conservative aggregate reserve USD 0.88834575. No top-up or scheduled further call. These are not independently audited invoices.

Native Windows, backend/frontend tests and contract checks pass. Formal team release and reviewed browser/human acceptance are separate work. See FINAL_DELIVERY_REPORT.md and DAY4_HANDOFF_TO_DENG.md.
