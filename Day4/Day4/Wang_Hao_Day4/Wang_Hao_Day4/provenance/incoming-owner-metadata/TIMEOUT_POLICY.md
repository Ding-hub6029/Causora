# Unified Day4 timeout policy

Current OpenRouter policy; old 8/12-second defaults or old 10/12-call examples remain historical, not current settings.

| Layer | Default / limit | Source |
| --- | --- | --- |
| Ding frontend Boardroom wait | 45 seconds, unchanged | frontend/lib/boardroom-api.ts |
| Whole AI pipeline | 40 seconds maximum | PipelineConfig.total_timeout / CAUSORA_AI_TOTAL_TIMEOUT |
| CFO/COO/Risk, Synthesizer | 10 seconds maximum each | stage_timeout / CAUSORA_AI_STAGE_TIMEOUT |
| Both Gemini and GPT Critic | 15 seconds maximum each | critic_timeout / CAUSORA_CRITIC_TIMEOUT |
| SDK effective call deadline | Exact remaining pipeline stage budget | request_timeout / client.with_options |
| SDK/pipeline automatic retries | Zero in OpenRouter mode | max_retries=0 / config retries=0 |
| Shared paid request quota | Six cumulative journal slots | OpenRouterBudget and pipeline config |
| Client cleanup | Parallel; each <=1 second | Adapter finally block |
| Budget sidecar lock wait | Five seconds, no unprotected dispatch | portalocker bounded exclusive acquisition |

Providers are configured from one factory-returned config. Before each dispatch effective timeout is min(configured stage limit, remaining global time minus following-work reserves). Exact value reaches both SDK and asyncio. Preferred Critic reserves possible fallback/synthesis/return validation; fallback reserves synthesis/return validation; synthesis reserves return validation. Default following-stage reserve five and return reserve one seconds are scheduling reserves, not competing Critic defaults. No remaining time means no request.

The global monotonic timer includes source and role preparation; integrated OpenRouter preflight also shares it. Retries/fallback cannot renew the global deadline. Cleanup is bounded/concurrent, leaving frontend margin. Operating-system stalls, filesystem/network-share behavior or arbitrary external blocking code are not covered by an absolute timing guarantee.

A real asyncio preferred-Critic timeout cancels its task and attempts a labelled fallback within remaining budget. Failure of both Critics publishes no Brief; single role timeout prevents synthesis. Cancellation never clears/reruns simulation matrix/deltas/traces. Unknown remote costs retain reservations even when cancellation/timeout prevents response settlement.

Local delayed fixtures verify timeout/cancellation, completed fallback and identical effective SDK-facing budgets. SDK tests check both Critics and environment precedence. These are **local tests**, not Gemini network success or a real remote forced-timeout experiment.

Current actual network workflow wall time **28.901047 seconds**, including verifier read-only preparation/final evidence; runtime forty/ten/fifteen settings. Gemini returned provider_bad_request after 2.470234 seconds, **not a timeout**. GPT fallback returned after 11.294471 seconds but failed Numeric Scan; no Synthesizer. Thus the observed failed run stayed below frontend forty-five seconds, but does not prove successful Gemini/fallback/Synthesizer network completion or worst-case Windows latency.

```text
CAUSORA_AI_TOTAL_TIMEOUT=40
CAUSORA_AI_STAGE_TIMEOUT=10
CAUSORA_CRITIC_TIMEOUT=15
CAUSORA_AI_RETRIES=0
CAUSORA_AI_PIPELINE_CALLS=6
CAUSORA_AI_MAX_CALLS=6
```

Historical experimental timeout audits retain old timestamps/values, not current acceptance. No additional key use/model request followed this verification.
