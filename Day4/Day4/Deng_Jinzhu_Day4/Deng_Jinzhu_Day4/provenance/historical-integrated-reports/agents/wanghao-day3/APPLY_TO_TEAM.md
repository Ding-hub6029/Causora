# Apply to the team — latest Day3 Monte Carlo integration

## Ownership

Keep Wang's directory separate. **Do not overlay this archive on Ding's frontend or Jinzhu's backend.** Ding remains final integration owner; Jinzhu's engine is unchanged. Wang's package.json is only for standalone contract tests, not a website build file.

Current integration uses the latest backend's unchanged `POST /api/simulate` with a v1 request and v2 development success. The old v6 deterministic bridge is retained only for history/legacy testing and is not used by the current `mc_cli` or default suite.

## Backend-owned development wiring

```python
from agent_day3.mc_client import post_simulation
from agent_day3.mc_roles import run_mc_parallel, DevClaimStubProvider

# Exact request sent to the explicitly launched latest unreviewed service.
capture = post_simulation(service_base_url, request_v1, enabled=True)
roles = await run_mc_parallel(
    capture['request'], capture['response'],
    provider=DevClaimStubProvider(),  # explicitly OFFLINE_STUB; optional model separately
    scenario_id='demand-drop', enabled=True,
    headers=capture['transport']['headers'],
)
```

Use the newly captured request/response pair and preserve its transport digests. Prefer the CLI `fetch-analyse`/`analyse` boundary and immutable capture store. Low-level raw-dict helpers validate duplicated request facts and response consistency but are **not** cryptographic proof of the originating HTTP exchange; do not bypass transport/digest storage or construct fake captures. If an input changes, call the service again, not `run_mc_parallel(new_request, old_response)`.

The returned internal object is **not an AgentOutput/BoardroomResponse or recommended winner**. It retains executionContext verbatim, original simulationId/dataVersion/scenarioId/requestId, raw JSON request/response hashes, actual MC count, provider kind and three stable-order DEV_ONLY/UNAVAILABLE outputs. `ALL_READY` means valid role selections/rendering only.

## Field isolation

| Role | Allowed numeric inputs | Explicitly excluded |
| --- | --- | --- |
| CFO | expectedTco, five cost components, cashOutflowP90, D0-relative TCO/cash deltas | Operational probability/service/units, legal clauses, PDF content |
| COO | selected demand/lead inputs, mean purchase units, reorder thresholds, stockoutProbability, serviceLevel and service/risk deltas | TCO, cash amounts, clauses, PDF/evidence records |
| Risk | probability, P90, feasibility, request risk/budget limits, limited unreviewed contract parameters and development status | TCO/full financial breakdown, full operating paths/inventory, PDF/source files |

Common simulation/data/scenario/option identity is allowed. No role receives full matrix, full trace/sample path, selection/recommendedOptionId, raw source paths/quotes or human receipts. No revenue/profit is invented because the v2 HTTP DTO does not supply those metrics.

Every selected metric uses a `response:/...` or `request:/...` canonical JSON Pointer. Its typed binding includes document/pointer, value, simulation/data/scenario/option identity and response digest. Bindings are re-read from private deep copies after the provider returns. Providers can select only code-verified claims; they cannot create prose/numbers/recommendations. Single-role errors/timeouts do not erase the other outputs; external cancellation propagates.

## Request freshness and actual statistical meaning

Baseline, demand-drop and lead-stress were all analysed in four newly requested HTTP captures. Demand changed from -15%/22,100 units to -25%/19,500; lead stress changed from 1.3 to 1.8. Each changed computation has a new simulationId and numerical results. Same source dataVersion is correct; it is not a per-request counter. Browser integer numeric spellings are supported without changing source hashes or pretending a new dataset exists.

Use returned `stockoutProbability` with its numerator/MC denominator and `cashOutflowP90` with its specified rank/method. Never transform `stockoutOccurred` into probability or `cashOutflowUsd` into P90. One 104-week sampleRunIndex=0 path is not an aggregate; the validator does not reconstruct a distribution from it.

## Review and frontend boundaries

Current review format: **reviewed_contract.json + review_record.json**. See `evidence_review/FORMAL_REVIEW_FORMAT.md` and `mc_review_compat.py`. Original eleven pending decisions and empty signer fields are preserved; the delivered native worksheet is deliberately non-verifiable. Genuine positive review consumption remains unexecuted.

The supplied v2 schema/TypeScript recommendation is consumed only by Wang's development adapter. No shared production contract or Ding frontend file was changed. Ding must confirm/migrate v2 runtime types and preserve all development markers under the team release process; Wang's internal role sidecar is not a proposal to extend Ding's public AgentOutput. Do not pipe backend `selections` into a formal Boardroom recommendation.

The latest backend's default formal mode remains 503 without review/policy/release. The old Wang formal snapshot checks remain intact; neither can be bypassed by these development outputs.

## Remaining

Genuine eleven-item human review; team policy confirmation; three-owner v2 release and Ding's actual frontend integration; independent Critic label review/freeze; future complete Critic/Synthesizer/final Numeric Guardrail and final acceptance. This revision deliberately does not perform Day4 stages or invent approval.
