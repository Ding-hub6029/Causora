# Wang Hao Day5 Offline Reliability Tests

All results are TEST_FIXTURE_ONLY. Providers use deterministic in-memory responses. Clear OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_BASE_URL and OPENROUTER_API_KEY before running. Do not describe fixtures as real calls, model recall or human approval.

Reference regressions were selectively adapted rather than overwriting implementation directories. day5_fixtures supplies reviewed inputs, in-memory providers and selection recalculation. Pipeline reliability covers five stages, missing/timed-out/malformed Critic fallback, identity and no-feasible handling, numeric and percentage-point tampering, D1 mixed allocation, D2 B-only semantics, Matrix/Trace preservation, evidence injection and malformed JSON. Budget portability covers local journal/portalocker spawn and thread cases without HTTP or runtime changes. OpenRouter tests fake /models, /key and completions in memory.

```bash
python -m pytest tests_day5 -q -p no:cacheprovider
```

run_offline_ai_evaluation.py writes per-case JSONL and summaries. semantic_false_acceptance is a known unresolved limitation, not a passed safety detection rate.
