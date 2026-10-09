# Day 4 Integration Plan — Completed Technical Merge and Remaining Release Steps

The incoming planning document is preserved at `provenance/ding/incoming_frontend_baseline/INTEGRATION_PLAN.incoming-2026-10-08.md`. This file is the current plan for the combined package.

## Completed

| Workstream | Completion evidence |
| --- | --- |
| Three-way merge | Ding frontend preserved. Deng service/engine and Wang AI module selectively integrated. |
| Simulation/Trace identity | v2 response contains current Matrix, Delta, selection, traces, and per-run correlation. |
| PDF Evidence | EV-024 source quote, current-run locator conversion, and browser highlight completed. |
| AI boundary | Current Wang module lazy-loads only for formal reviewed runs. Development Boardroom is rejected. |
| Deadline/budget controls | Wang pipeline/provider code and offline tests retained. |
| Performance | Fixed-seed current-engine N=1,000 and N=10,000 captures complete. |
| Documentation | Current merge, interface, startup, G4, and validation reports added. Historic reports preserved. |

## Remaining release workflow

1. Install Wang's actual reviewed contract bundle. Run normal reviewed simulation and verify changed reviewed fields alter the calculation.
2. Record the three-owner policy approval and Trace-v2 release record against the current package hashes.
3. Run normal reviewed service mode and verify a reviewed v2 Matrix/Trace response.
4. Obtain explicit authorization and a private OpenRouter key. Run one bounded preflight and formal Boardroom request with a persistent journal.
5. Run Ding's reviewed browser E2E test for the same run. Inspect cited Evidence, Boardroom/Critic, Brief, and human decision state.
6. Obtain actual team G4 acceptance outside the application.

## Invariants

- Do not substitute a saved example, fixture, or unreviewed run for the reviewed workflow.
- Do not recompute Monte Carlo on an AI retry/timeout.
- Do not call a provider from a development run.
- Do not package secrets, runtime caches, provider journals, `node_modules`, or virtual environments.
