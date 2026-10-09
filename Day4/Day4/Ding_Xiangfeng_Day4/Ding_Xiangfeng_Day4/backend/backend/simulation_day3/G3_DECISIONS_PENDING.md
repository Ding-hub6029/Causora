# G3 Model Clarifications Pending Joint Agreement (Historical)

Deng's synthetic-computation proposals are not Wang review or permission to treat internal results as recommendations. Original shared v1/TS/mock/Golden remain unchanged. Current fifteen-topic policy requirements are in MODEL_POLICY_CONFIRMATIONS.md. This earlier table groups topics differently and is historical.

| Existing definition | Proposed agreement | Reason / affected modules |
| --- | --- | --- |
| PDF p.11: >=52 demand weeks. 104 observed total 25,936. Frozen forecast 26,000 | Bootstrap 104 rows, explicitly scale scenario forecast/25936, allow each trial total to vary | Preserve sampling uncertainty. History is not locked forecast. Engine, ScenarioLab, trace. |
| PDF p.11: >=30POs for empirical sampling. A 36/B 12 | A empirical. B triangle10/14/17 user-assumed only after written confirmation, or collect >=30 POs | Twelve cannot support claimed high-confidence empirical fit. Engine/provenance/UI/tests. |
| Reorder=mean demand xmean lead+safety. Externalstress | Raw A 36-PO mean and B theoretical mean fixed policy, explicitly A_only/all_suppliers stress | No reverse policy from random trial means. A-only leaves D2 unstressed. Engine/UI/sensitivity. |
| v1 unitsA/B integers. Client purchase reconciliation | Round mean D0/D2 units half-even, recompute purchase/premium, retain raw means in trace. Agree before decision | Integer wire cannot losslessly encode floating means. Engine/DTO interpretation/validator/finance. |
| Cash P90 definition incomplete. Loss opportunitycost | Pertrial purchase+holding+premium+one exit, half-even each full-horizon line, nearest-rankceil(.9N),exclude loss | Reproducible risk measure, not extraTCO fee. Engine/API/UI/oracle. |
| Renewal11/18,inventoryCSVdecision10/4 | Confirm bridge, saleprice, lost margin, holding, target/safety, order recognition. Examples test-only | Wrong-date inventory corrupts paths/risk. Inputs/engine/source audit/thresholds. |
| v1 no weekly/gross margin fields | Internal auditable traces. Agree authenticated retrieval or newversion | No silent v1extensions. Contract/backend/trace UI. |
| Six clause/five assumption pending at original delivery | Wang personally reviews sources/bundle. Separately approve policy before formalPOST200 | Synthetic review is not realcontract verification. Computed risk doesn't lift gates. Evidence/engine/API/approval. |

No changes are enacted by this table. Agreed semantic changes require coordinated API_CONTRACT, contracts.ts, types.ts, mock, Golden and contracttests before release. Rejected proposals require rerun/impactrecord. Later supplied humanreview is recorded separately, without retroactively signing this table.
