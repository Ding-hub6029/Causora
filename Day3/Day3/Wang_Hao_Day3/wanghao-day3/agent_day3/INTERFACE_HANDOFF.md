> **Legacy v1 formal/mock protocol reference, not the current MC runbook.** Latest-Day3 development uses the new `mc_*` modules against Jinzhu's actual HTTP MC service. Follow the root README/APPLY_TO_TEAM.md and native two-file review document. This older normalized-number hash/snapshot protocol is not used by the MC capture protocol, whose hashes preserve original JSON spelling.

# Wang Hao Day 3 — independent interface handoff

## Freeze and ownership

`reference/API_CONTRACT.md` and `reference/contracts.ts` are read-only shared contracts. This module adds **no** HTTP DTO and does not produce `BoardroomResponse`. It is an internal role-draft stage after a future simulation response.

| Owner | Day 3 consumes | Day 3 does not own |
| --- | --- | --- |
| Dingxiangfeng | Frozen fixture shape / eventual UI integration. | Frontend files, site build, UI status mapping. |
| Jinzhu | Typed simulation, selection, request/engine provenance, verifier callback. | Cell computation or live-status inference. |
| Evidence reviewer | Backend dataset success plus hash-bound human receipt. | AI-to-human promotion, source preprocessing, real-world claim. |
| Wang Day 3 | Strict validation, projections, async isolation, draft. | Critic, synthesis, Brief, numeric final guardrail, approval. |

## Strict models and cross-boundary invariants

`wire_models.py` uses `strict=True`, `extra="forbid"`, frozen models and finite-number validation. Future fields are rejected, not forwarded.

| Object | Enforced invariant |
| --- | --- |
| `EvidenceRecord` | `EV-###`, page >=1. Bbox is null or exactly four finite non-negative increasing coordinates decoded from JSON list to tuple. |
| `ContractConstraint` | Valid calendar dates and exact intervals. Unique evidence IDs. Exact whole-unit purchase floor. |
| `MetricCell` | Integer TCO exactly equals five integer breakdown fields. Units are integers. No zero total procurement. |
| `SimulationResult` | Unique option cells per scenario. Explicit prices, seed, horizon and run count. |
| `BoardroomSnapshot` | Exactly ordered D0/D1/D2 and same-order cells. Each cell's A/B ratio binds its referenced option. Evidence order binds the contract. |
| `SIMULATION_READY` | Reference binds schema/data/simulation/scenario/options plus simulation and full-input SHA-256. Selection is recomputed from feasibility, inclusive risk/cash limits, and deterministic eligible-TCO ordering. |

`monteCarloRuns=0` is accepted for a genuine deterministic computation but is never used as a mock/live discriminator.

## Verification boundary

### Local mock

`load_local_mock_snapshot()` resolves this module's own `../fixtures/causora_day1_mock.json`, strict-validates it, and `verify_snapshot` compares the caller value to it. Local mocks cannot carry a selection/reference/review bundle and every output stays `MOCK`, `decisionReady=false`.

### Real simulation

`load_real_snapshot_input(path)` accepts only the explicit hash-bound input protocol described in the README. Before any provider task, `run_parallel`:

1. requires `review_bundle/dataset_success.json`, `review_scope.json`, and `human_receipt.json`.
2. validates matching dataset/scope/receipt hashes, nonempty source hashes, `reviewerType="human"`, `allApproved=true`, named UTC reviewer, six approved evidence IDs, and all five approved assumptions.
3. requires the reviewed dataset's exact data version, contract, and evidence to equal the simulation input. Unmatched evidence cannot reach Risk.
4. requires and invokes Jinzhu's verifier callback. Missing/failing verifier fails closed. And
5. skips all model calls for a verified `no_feasible_option`.

The receipt is an integrity gate, not reviewer-identity authentication or real-world verification. A pending AI review is never a human receipt. This module does not ship a no-op verifier.

```python
from agent_day3.models import BoardroomSnapshot

def verify_simulation(snapshot: BoardroomSnapshot) -> None:
    """Jinzhu/backend-owned: raise unless immutable engine request/result match."""
    # Verify engine-owned request inputs, result digest, selection and provenance.
    raise NotImplementedError("Replace with Jinzhu's independently checking verifier, never use a no-op")
```

## Exact provider projections

Only these typed Pydantic objects are serialized to providers. PDFs, quotes, full fixture blobs, arbitrary dictionaries, review receipts, and source paths are withheld.

| Role | Allowed | Withheld |
| --- | --- | --- |
| **CFO** | Per-option TCO, cash P90, D0 delta, five cost lines. | Contract/evidence, stockout/service/lead time, operations. |
| **COO** | Demand, lead time, per-option stockout/service and A/B units. | TCO/cash/breakdown, contract/evidence, feasibility/selection. |
| **Risk** | Quote-matched evidence IDs only, matched clause/derived state, uncertainty/run count, feasibility/cash P90/stockout downside. | Quote/PDF/source path, TCO breakdown, service/allocation units, full receipt. |

Allowed metric/evidence references are generated from the concrete validated projection. Provider schema and Pydantic both reject cross-role refs, unknown fields, duplicate refs, invented options, and numeric/template prose.

## Execution and output

All three role tasks are created before `asyncio.gather`. Timeout, invalid provider response, provider exception and internal cancellation are isolated by role. Caller cancellation propagates and exception text is never emitted.

The sole handoff is:

```text
Day3AgentDraft {
  kind: "CAUSORA_WANG_DAY3_AGENT_DRAFT_V1",
  agentOutputs: AgentOutput[3],  // CFO, COO, Risk only
  criticStatus: "NOT_IMPLEMENTED_DAY3",
  decisionReady: false
}
```

It deliberately omits `brief`, `criticIssues`, `numericGuardrail`, a recommendation and any approval. The adapter's `metrics` are the provider's actual validated refs—not unrelated hard-coded display IDs. Do not cast it to `BoardroomResponse`.

## Final audit clarifications

The six human-approved IDs must be exactly EV-014, EV-019, EV-021, EV-024, EV-027 and internal EV-020. The callback is synchronous, returns None only on successful independent checking, and cannot mutate the detached input. Whole-valued float and integer number spellings normalize identically in the internal digest protocol described in README. The frozen mock simulation ID cannot be promoted by changing sourceMode.

The digit/template scan is not the complete Day 4 Numeric Guardrail. Spelled numerical words and unsupported qualitative commentary require later Critic/content review. `ALL_READY` means schema-valid role drafts, not semantic accuracy or approval. See `reports/MODEL_SMOKE_REVIEW.md` from the package root.
