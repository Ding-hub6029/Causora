# Causora Day 1 — Team Integration Handoff

## Ownership

| Person | Day 1–Day 7 owner | What this prototype gives them now |
| --- | --- | --- |
| **Xiangfeng Ding** | Product + Integration Lead | Next.js visual workflow, complete local-mock Golden Run, README, Devpost skeleton, responsive QA and a proposed versioned API contract. |
| **JINZHU DENG** | Simulation + Data Lead | Typed `Scenario`, `DecisionOption`, `ContractConstraint`, `SimulationResult`, `DecisionDelta`, versioned five-line TCO, units, and deterministic seed. |
| **Wu Wang** | AI + Evidence Lead | Typed `EvidenceRecord`, five mapped `BusinessVariable` objects (including EV-019), structured `AgentOutput` / `CriticIssue` / `DecisionBriefRef`, and numeric-token rendering. |

## Day 1 Mock Contract

- **Canonical front-end input:** `demo_data/causora_day1_mock.json`
- **Full frozen Golden fallback:** `golden/golden_run.json` (independent `snapshot` + SHA-256)
- **Shared TypeScript entity contract:** `lib/contracts.ts`; frontend adapter: `lib/types.ts`
- **Proposed endpoint, error, unit and version contract:** `API_CONTRACT.md` (read before Day 2 implementation)
- **Synthetic source fixtures:** `public/demo/` including six-page searchable agreement and notice register
- **Visible stage IDs:** `intake`, `scenario`, `matrix`, `boardroom`, `brief`
- **Fixed option IDs:** `D0`, `D1`, `D2`

No team member should silently rename these IDs without updating the JSON, the type contract, the tests, and the relevant UI copy in one pull request.

**Freeze meeting before parallel integration:** Xiangfeng, Jinzhu and Wu must jointly review `API_CONTRACT.md` v1, agree on camelCase fields and numeric wire units, confirm that the 14% Supplier A uplift appears exactly once (base-price purchase + premium line), and confirm that the 60% minimum is against the 26,000-unit synthetic forecast locked for the renewal cycle. **D1 must also purchase exactly 60% A / 40% B in every preset**, including demand drop (15,600 A + 10,400 B); procurement may exceed realised demand, but the ratio cannot silently change. Document any different real-contract interpretation before changing code. The API endpoints described in the contract are **not implemented** by this Day 1 static frontend.

## Proposed Branches

```text
feature/xiangfeng-ui
feature/jinzhu-simulation
feature-wuwang-evidence-agents
```

## Merge Discipline

1. Keep `main` runnable after every merge.
2. Integrate twice daily: once at midday and once in the evening.
3. Stop broad schema changes 30 minutes before an integration window.
4. Announce every cross-module schema change with an English field-level summary and updated mock JSON.
5. The module owner merges; other members review instead of editing the same core file in parallel.

## Replacement Sequence for Day 2+

1. JINZHU implements `POST /api/simulate` and returns a `SimulationResult` containing unique option cells, their component breakdowns, seed and formula version. Do not rewrite display strings in the backend.
2. Wu Wang implements the Evidence/BusinessVariable adapter plus `POST /api/boardroom`; reconcile all five quote/page references with source PDF(s), and never claim a real notice was not sent based solely on the synthetic register.
3. Xiangfeng validates `schemaVersion`, swaps the local data adapter to the approved backend responses and handles loading, errors, draft recalculation and `no_feasible_option` before permitting live approval.
4. Keep the bundled Golden Run **local-mock labelled**. After a fully audited backend run, freeze a new production snapshot with its real timestamp and validated hash; do not confuse the two.

## Required Integration Check

After either data adapter changes, run:

```bash
npm run typecheck
npm run lint
npm test
npm run build
```

Then manually traverse Input → Scenario → Matrix → Boardroom → Brief once before merging.
