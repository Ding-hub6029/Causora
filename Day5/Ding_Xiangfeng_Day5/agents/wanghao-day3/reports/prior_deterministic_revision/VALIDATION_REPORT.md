# Validation report — Wang Hao Day 3 development compatibility revision

Recorded on 2026-10-07 (UTC+08:00). This report supersedes the older report in `prior_revision/`.

## Observed results

| Check | Actual result | What it does not prove |
| --- | --- | --- |
| Wang complete suite, external Jinzhu workspace explicitly configured | **100 passed** in 19.08 seconds; `reports/final_tests.log` | Human approval, production acceptance, deployed team E2E, or Critic accuracy |
| Supplied Jinzhu Day1/Day2 baseline regressions | **37 passed; 25 subtests passed** | Day3 Monte Carlo statistics or a deployed service |
| Actual deterministic calculation through bridge | **9 cells × 104 weekly rows = 936 audited rows**, all reconciled | Real supplier facts, approved policy, probability/P90 |
| Independent trace audit | Reconstructs historical allocation, inventory flow, orders, arrival seed/lead timing, commitment quotas and Decimal accounting; no private calculation helper used as oracle | Formal causal/legal/business correctness of unapproved assumptions |
| Three offline scenario smokes | Baseline, demand-drop and lead-stress: **ALL_READY**, three role outputs `DEV_ONLY` | AI-authored commentary or a recommendation |
| Real model-proxy selection smoke | **ALL_READY**, actual `gpt-5-mini`, actual computed demand-drop inputs; three `DEV_ONLY` outputs | Optimality or final content completeness |
| Current saved model sample re-render | Every claim/ref/value/narrative matches current code catalog and typed view | Broader free-form model correctness |
| Real local HTTP round trips | `/dev/health` 200; `/dev/analyse` 200 with all three DEV_ONLY outputs; formal `/api/simulate` **503 human_review_pending** | Three independently deployed owner services or Ding's live UI |
| Shared TypeScript contract check | **Passed**; `reports/ts_contract.log` | Frontend website build |
| Original shared files | API_CONTRACT.md and contracts.ts byte-identical across supplied Ding Day3 and Jinzhu packages; no changes made | Approval of any future contract amendment |
| Human review state | All **11** decisions pending; all confirmed values null; reviewer/timestamp blank | Any human sign-off |
| Package integrity | SHA-256 manifest, no site/owner-engine overlay, ZIP CRC and credential-value scan | Reviewer or source identity authentication |

## Commands executed

```bash
CAUSORA_JINZHU_ROOT=/path/to/combined-source-root python -m pytest -q \
  agent_day3/tests agent_day3/evals/test_corpus.py evidence_review/tests
python scripts/check_contract_types.py
npm run test:contract
python -m compileall -q agent_day3 evidence_review scripts
```

The explicit workspace contains unchanged files assembled from the supplied Jinzhu v6 and Wang Day2 review-pending archives. External-engine tests do not silently count unavailable dependencies as successes; they report skips if a workspace is missing. The full passing result above used a real configured workspace, not skipped integration tests.

## Coverage highlights

- Formal gate remains required, including exact six evidence IDs and five assumptions.
- Direct original review format dispatch must call the original verifier; a pending/incomplete bundle cannot be consumed or converted.
- The optional wrapper's positive test uses a named **test double** in a temporary test directory; no genuine signed review was supplied or generated.
- Development is explicit opt-in; status/version/hash/source/audit substitution fails before provider calls.
- Same-preview-ID numerical tampering, wrong weekly arrival/summaries/margins/seed/source hashes, duplicate or missing cells, wrong policy, and false stockout flags are rejected.
- CFO/COO/Risk payloads contain only their own typed view and code-authored claim catalog; no full matrix, traces, PDF quotes, source paths or human receipt reach providers.
- Concurrent start barrier, per-role timeout/failure/cancellation isolation and outer cancellation propagation are covered.
- Unsupported claims, free reason text, numeric spelling, unsupported remote-schema keywords and duplicate claim IDs are covered.
- Critic development/held-out input separation, input hashes, label-free loading and scoring denominators are covered. Formal scores remain disabled on draft labels.

## Explicitly incomplete formal acceptance items

1. The six evidence and five demonstration assumptions have **not** received genuine human sign-off.
2. The physical/financial policy is an **UNAPPROVED_TEST_INPUT** with a hypothetical horizon-opening inventory; it is not silently replaced by the different dated CSV inventory.
3. The supplied backend has **zero Monte Carlo runs**, no probability/P90 metrics, and no Day3 success result. Only its actual deterministic function has been integrated for development.
4. No separate Jinzhu hosted Day3 service URL or Ding live UI integration was supplied/exercised. The HTTP check was a temporary Wang harness calling Jinzhu's unchanged functions locally; it was stopped after testing.
5. Critic labels need independent review/freeze; no official catch rate or false-positive rate was measured.
6. Critic, final numeric guardrail, Synthesizer, Brief and final team acceptance are not fabricated.

**Honest status:** owner-module development and compatibility testing completed on the supplied deterministic engine; manual review and genuine Day3 Monte Carlo / final team integration remain pending. These are deferred acceptance requirements, not failed automated tests.

## Clean-extraction portability check

A candidate owner-only ZIP was extracted into a new directory. A new virtual environment installed `requirements.txt`, and a **new** dependency workspace was reconstructed from the two supplied archives. The clean-extraction suite again returned **100 passed in 19.97 seconds**, package SHA-256 verification passed, TypeScript compilation passed, and an actual-engine offline development analysis returned `ALL_READY` with `DEV_ONLY` outputs and no approval. Logs are `fresh_install_tests.log` and `fresh_install_types.log`. The final ZIP differs from that tested candidate only by documentation/history placement and saved validation logs; executable modules are unchanged.
