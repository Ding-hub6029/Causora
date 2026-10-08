> **Legacy v1 formal/mock protocol reference.** Current latest-Day3 development uses `mc_cli`, `mc_client`, `mc_validation` and `mc_roles` against Jinzhu's actual HTTP Monte Carlo service. See the root README/APPLY_TO_TEAM.md and native review FORMAT document. The old deterministic `dev_cli` is not the current target; the following v1 gates remain separate and do not accept the unreviewed MC sidecar.

# Wang Hao Day 3 — independent role-draft module

This is **Wang Hao's module only**. It does not alter Dingxiangfeng's frontend, package a website, change the shared contract, import `simulation_day1`/old evidence preparation, or implement Jinzhu's simulator.

## Behavior

- Independent strict Pydantic v2 wire models reject unknown fields, non-finite values, bad dates/bboxes, missing/duplicate option cells, invalid fixed D0/D1/D2 semantics, allocation-ratio mismatches and non-exact integer breakdown sums.
- The unchanged `../fixtures/causora_day1_mock.json` is source-hash pinned. Old ZIPs and a merged frontend are not needed.
- `run_parallel` creates **CFO, COO and Risk** tasks before awaiting any, and gathers in stable role order. Per-role timeout/provider/invalid-response failures are isolated; external cancellation propagates. A verified no-feasible result makes no provider calls.
- Only typed allowlists cross the provider boundary: CFO finance; COO operations; Risk matched clause IDs/values, downside and uncertainty. No raw PDF, quote, source path, full matrix dictionary, human receipt or arbitrary extra field enters role prompts.
- Metric/evidence refs must belong to the role projection. Option-specific metric refs must resolve to declared option IDs. Provider payload/schema copies cannot expand the trusted allowlist.
- Inputs are revalidated and detached before verification. The verifier must be synchronous, return `None` on success or raise on failure, and may not mutate the snapshot. An unawaited async verifier is rejected.
- The adapter emits only `AgentOutput[]` in an internal `Day3AgentDraft`, **not** `BoardroomResponse`. No Critic, Synthesizer, Brief or approval is fabricated; `decisionReady` is permanently false.

## Install / test from the extracted package root

```bash
python -m pip install -r requirements.txt
python -m pytest -q agent_day3/tests agent_day3/evals/test_corpus.py evidence_review/tests
python -m agent_day3.cli offline-mock --scenario demand-drop
```

Use Python 3.11+; the observed environment was Python 3.12.3. On Windows, `python -X utf8` is recommended. All file operations explicitly use UTF-8. Tests and offline CLI do not call a provider. `openai` is used only for the opt-in server-side adapter.

The default CLI action is `offline-mock`. Offline results are `LOCAL_MOCK / OFFLINE_STUB`, never AI-generated decisions. To save a new audit output:

```bash
python -m agent_day3.cli offline-mock --scenario baseline --output local-baseline.json
```

Existing audit files are not overwritten.

## Optional model smoke

```bash
# Authorized server-side environment only; check the provider's current catalog first.
# The adapter currently uses GPT-family parameter syntax.
python -m agent_day3.cli model-mock-smoke --scenario demand-drop \
  --model gpt-5-mini --output new-model-mock.json
```

Provide `OPENAI_API_KEY` and `OPENAI_API_BASE` through server environment variables; never send them to frontend code or put them in ZIP/config files. Provider credentials are not included. This legacy command remains **LOCAL_MOCK**, regardless of an actual model response. Historical mock smokes are archived under root `reports/prior_revision/`; the current root model report instead concerns the new MC flow.

**Narrative safety limit:** the Day 3 parser rejects digits and template braces and requires structured refs. It does not implement the full Day 4 Numeric Guardrail: spelled-out numbers, qualitative unsupported claims and cross-role omissions still need Critic/content review. Schema-valid `ALL_READY` means three role drafts were available, **not** that the commentary or a decision is correct.

## Real SimulationResult integration

The input protocol is **internal**, not a new public HTTP DTO. `RealSnapshotInput` requires:

```text
schemaVersion, dataVersion, scenario, options, simulation, contract, evidence,
selection, selectionLimits {riskThreshold, budgetCeilingUsd},
reference {schemaVersion, dataVersion, datasetId, simulationId, scenarioId,
           optionIds, simulationSha256, snapshotSha256}
```

**Jinzhu does not need to add any field to his API.** Wang/backend code can call `agent_day3.integration.from_shared_records()` with the unchanged DatasetSuccess, the stored SimulateRequest's scenario/options/limits, and SimulateResponse's simulation/selection. This assembler creates the private reference/hash metadata locally. Hash construction is not authentication; the independent engine verifier still must check the trusted original records.

`simulation` is the unchanged shared `SimulationResult` shape. The backend provides the applicable Scenario/DecisionOptions/Contract/Evidence and immutable selection alongside it; SimulationResult alone does not contain those inputs or the eligibility thresholds.

The full-input digest covers all root fields **except `reference`**. Use `agent_day3.wire_models.sha256_json()` consistently: sorted keys, UTF-8, no whitespace, finite numbers, and whole-valued floats normalized to integers, so JSON `0` and `0.0` have the same semantic digest. This is a documented internal protocol, not a claim of RFC 8785 compliance. `simulationSha256` covers the entire serialized SimulationResult, not only the requested cells. Direct snapshots are checked against the full-input digest too.

The selection is independently rechecked per scenario: feasible, stockout <= threshold, cash <= ceiling; then minimum TCO with option-ID tie-break. All ordered violations must match. This is validation of the supplied result, **not re-running the simulation**.

### Human-review bundle gate

| File | Required binding |
| --- | --- |
| `dataset_success.json` | Backend-produced unchanged v1 DatasetSuccess envelope. |
| `review_scope.json` | `CAUSORA_EVIDENCE_REVIEW_SCOPE_V1`, schema/data version, canonical dataset digest and nonempty source-hash map. |
| `human_receipt.json` | `CAUSORA_HUMAN_REVIEW_RECEIPT_V1`, `reviewerType=human`, `allApproved=true`, name/UTC time, current scope/dataset/source hashes, exactly EV-014/019/021/024/027/020 and all five assumption keys. |

The receipt is an integrity/trusted-server gate, not authentication of human identity or proof of real facts. The current AI-reviewed candidate with **human pending / not verified / NOT_COMPUTED** cannot satisfy it. Do not create a receipt by changing those flags. The backend must perform authorized source review and retain a genuine attestation.

### Simulation-owner gate

Jinzhu must provide a real verifier callback that independently checks engine-owned request inputs, dataset, seed, formula version, matrix, selection, result digest and provenance; it must raise on mismatch. A no-op callback is invalid production integration. Neither a positive nor zero `monteCarloRuns` count establishes origin. Deterministic computation may use zero runs; the frozen mock simulation ID cannot be relabelled `SIMULATION_READY`.

```bash
python -m agent_day3.cli real-integration \
  --input-snapshot /secure/export/simulation_snapshot.json \
  --review-bundle /secure/export/review_bundle \
  --verifier my_backend.jinzhu_verifier:verify_simulation
```

The CLI intentionally uses an offline stub after validating both gates. For later provider integration, backend code may call `run_parallel(snapshot, provider=..., review_bundle=..., simulation_verifier=...)`. Even then it is a Day 3 draft, not a completed decision. See `INTERFACE_HANDOFF.md`; the module ships neither an engine verifier nor human-approved data.
