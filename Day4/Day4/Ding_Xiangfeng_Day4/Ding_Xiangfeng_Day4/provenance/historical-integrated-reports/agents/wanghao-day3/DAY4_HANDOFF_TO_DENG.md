# Current delivery status

See **FINAL_DELIVERY_REPORT.md** first. Native Windows regression is independently rerun in this delivery. Final-code native Gemini and Synthesizer workflow passed. Earlier NOT_RUN/NOT_COMPLETED wording below describes the superseded baseline; original documents are retained in verification/wang_day4/codex_final_revision/prior_delivery_documents. Team release approvals remain pending.

# Day4 handoff to Deng Jinzhu — portable budget

## Scope and preserved team boundary

Complete project, not a module patch. Ding frontend contracts and Deng simulation kernels are unchanged. Existing service registers already computed /api/simulate v2 success and installs app.boardroom_adapter; AI does not rerun MC. Original human reviews and pending policy/v2 release records remain byte-identical. This owner delivery is not three-person Day4 acceptance.

## Startup and imports

```bash
python scripts/setup_day4.py --verify
python scripts/start_day4_backend.py
# Explicit development mode, never implied review approval:
python scripts/start_day4_backend.py --development --port 8000
```

Both Python requirement lists now include portalocker>=3.2,<4. Windows pip resolves portalocker 3.2.0's pywin32 platform dependency. Native Windows tests passed independently; see WINDOWS_COMPATIBILITY.md.

Existing registration interface:

```python
from app.boardroom_adapter import register_simulation, install_boardroom_routes
record = register_simulation(
    request_dict, success, contract, evidence, source_root, simulation_request_id
)
install_boardroom_routes(app)  # idempotent; already wired
```

Arguments are the original validated v1 request, already calculated v2 success, actual computation contract, original evidence registry, pathlib source root, and response.requestId. Bounded immutable repository defaults to sixteen records/latest per dataset, process-local/single-worker. A restart needs an ordinary simulation request, not AI-triggered replay. Distributed simulation storage is separate team scope, not solved by the journal lock.

Formal owner API:

```python
from agent_day4.provider import providers_from_env
from agent_day4.pipeline import run_boardroom
primary, gemini, fallback, config = providers_from_env()
result = await run_boardroom(
    request, run=verified_current_run, provider=primary,
    critic_provider=gemini, fallback_provider=fallback,
    correlation_id=boardroom_request_id, config=config,
)
```

Use the factory-returned config, not a generic PipelineConfig default that permits formatting retries. OpenRouter mode forces six calls/zero retries. The HTTP adapter constructs providers lazily only after formal/current-run gates and closes unique clients with bounded concurrent cleanup. No-feasible-option constructs no provider.

VerifiedRun/validate_run preserves current request/response/contract/evidence/physical root, v2 identity, all matrix/trace cells, numeric costs/deltas/selection and source quote/hash closure. Evidence enrichment adds private typed provenance without changing public DTO.

## Unchanged public transport

POST /api/boardroom request: schemaVersion, simulationId, dataVersion, scenarioId. Success: existing v1 envelope plus current Boardroom requestId, dataVersion; data contains scenarioId, agentOutputs, criticIssues, brief, numericGuardrail. Roles CFO/COO/Risk in that order. Simulation request identity is separate from Boardroom correlation.

```text
X-Causora-Provider-Mode: primary | same-family-fallback
X-Causora-Critic-Status: complete
X-Request-Id: exact Boardroom request correlation
X-Causora-Current-Simulation: retained current simulation ID
Cache-Control: no-store
```

Existing CORS allowlists/exposed headers retained. Later new simulation rejects stale late AI response; physical source evidence checked again before publishing. GET /api/evidence/{id} keeps original Evidence DTO/current version. EV-020 clause-presence proof from the actual PDF uses source phrase automatically renews for public quote inclusion; it does not prove renewal has occurred.

## Isolation and D2 guarantees

CFO gets financial/cost/cash/delta fields; COO gets operations/demand/lead/inventory/allocation/stockout fields; Risk gets contract/downside fields. No full traces/credentials/source paths leak into role payloads. Common allocation facts do not add forbidden numeric fee/cash fields.

D2 terminates A and allocates sourcing to B, reduces A dependency, **not overall concentration or diversification**. All-A and all-B have the same internal planned-share concentration index; not a new public MC metric. Actual fee breakdown, stockoutProbability and cashOutflowP90/ceiling bind text checks across roles, Critic, synthesis/challenges and Brief. Correct warnings/negation/mixed alternatives remain valid.

Critic must cover all eight existing items and conditional compound mechanism. Synthesizer supplies exact option_action and cash_ceiling_enforced=true; only eligible existing options can be proposed and server choice remains authoritative. Fixed-floor excess is a benchmark difference, not total inventory; delta holding is observed, not automatic contract causation. Public templates remain exact allowlisted tokens, otherwise strict field-bound Numeric Scan. Rejected text is not cleaned into acceptance.

## Provider/budget configuration

OpenRouter exact models/base/parameters in OPENROUTER_INTEGRATION.md. Secure backend OPENROUTER_API_KEY only; explicit OpenRouter mode never silently uses Manus proxy credentials. Caller authorization uses CAUSORA_OPENROUTER_PAID_AUTHORIZED=YES and OPENROUTER_SCOPED_KEY_CONFIRMED=YES plus CAUSORA_OPENROUTER_BUDGET_JOURNAL at a persistent shared protected physical file.

Remote remaining may exceed USD one. Effective total dispatch ceiling is min(authorized USD 1, actual available) minus USD 0.05. Persisted count/expense/ceiling is authoritative across processes: no deletion, reset or separate journal for the same authorization. New sessions can only tighten. Unknown failure/cancel fees keep worst reserves; repeat marking cannot reduce expense. portalocker exclusive stable sidecar and fsync/closed-temp atomic replace support Windows/POSIX. Lock timeout/durable-accounting failure fails closed.

Global forty, role/Synthesizer ten, both Critics fifteen seconds; same effective budget reaches SDK and asyncio. Frontend remains forty-five. Integrated preflight shares global envelope. SDK/pipeline retries zero in OpenRouter config; explicit GPT Critic fallback is at most one labelled request. AI retry never recomputes MC. Local timeout cancellation tests do not certify actual network-timeout behavior.

| Failure | Existing transport behavior |
| --- | --- |
| Invalid/stale/model-output validation | 422 validation_error; no Brief |
| Timeout | 504 provider_timeout; successful simulation retained |
| Role incomplete | 503/504; no subsequent published analysis |
| Both Critics invalid/unavailable | 503; original matrix/deltas/traces retained |
| Non-ready/unreviewed formal record | 503 review_pending before model request |
| No feasible option | 200 existing no_feasible_option, null choice, no provider |

CancelledError propagates/cancels children; repository is not cleared.

## Development/real evidence status

Internal run_development_analysis returns a warning-bearing private draft, executionContext, decisionReady=false; not formal Boardroom success. Optional historical checkpoints remain explicitly identified developer-only, but **none were used in this validation**. Ding frontend requires explicit UNREVIEWED_DEV_ONLY opt-in even for dev simulation; formal Boardroom still refuses promotion.

Current final evidence is verification/wang_day4/codex_final_revision/final_accepted/final_openrouter_evidence.json. All five stages were fresh: three GPT roles, native Gemini Critic and GPT Synthesizer. Numeric/evidence/business checks passed, a private development Brief was generated, and simulation/traces stayed unchanged. Final source fingerprints match this run. Historical failures remain in their original paths. No further paid call is scheduled.

## Still pending

Fifteen policy approvals, v2/Trace release and reviewed Ding browser/team E2E remain separate team work. Keep twelve development/thirty blind held-out Critic inputs/draft labels; no official Day5 score is claimed. Native Windows and fresh model-module checks have passed; they do not sign human approvals or the team's final release.
