# Day 4 Changelog — Current Three-Owner Integration

The incoming Ding frontend changelog is retained at `provenance/ding/incoming_frontend_baseline/DAY4_CHANGELOG.incoming-2026-10-08.md`. The statements in that historic file about absent Boardroom/Evidence backend routes are superseded by this integrated package.

## 2026-10-08 integrated changes

- Retained Ding's public frontend flow, runtime contract checks, PDF.js viewer, and strict development/reviewed labels.
- Connected Ding's existing Evidence buttons to the same v1 Evidence endpoint when a current live development run exists. The change only enables source-locator inspection; it does not change a public DTO, accept an unreviewed Boardroom response, create a Brief, or enable a decision.
- Kept Deng's service/v2 Matrix + Formula Trace implementation and registered each successful run once for downstream Evidence/Boardroom correlation.
- Integrated Deng's real source registry and coordinate conversion. The server uses PyMuPDF for quote location, converts to PDF user-space, and the existing PDF.js viewer highlights it after viewport conversion.
- Imported Wang's latest `agent_day4` module and OpenRouter adapter behind the formal reviewed-run boundary. It preserves validated outputs, evidence validation, numeric guardrails, total deadline, cancellation propagation, process call cap, budget cap, and Windows-safe journal locking.
- Added/re-ran combined integration tests, offline Wang tests, deterministic N=1,000/N=10,000 benchmarks, HTTP smoke captures, and a real browser development flow.
- Added authoritative integration, merge, G4 status, fresh-validation, and startup documents. Incoming historical reports remain in `provenance/` rather than being relabelled as current acceptance.

## Deliberately unchanged

- Pending human review/policy/release files.
- Day 1/2 v1 input/error compatibility and core Monte Carlo calculation semantics.
- Ding's visible page flow and Wang's provider authorization requirements.
- All historical evidence and original human-review material.

## Current team state

The technical three-owner source integration is complete. Formal G4 is still **PENDING** because actual reviewed input records, three-owner approvals, and a separately authorized OpenRouter formal run have not occurred in this package.
