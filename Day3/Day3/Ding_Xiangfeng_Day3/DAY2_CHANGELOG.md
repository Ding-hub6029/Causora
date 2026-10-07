# Causora Day 2 — Change Log

## Front-end work owned by Ding Xiangfeng

- Reworked the Scenario Lab explanation so external **scenarios** and controllable **options** are shown as separate concepts.
- Added concise D0/D1/D2 descriptions using the existing fixed option IDs, allocations, contract minimum, and termination-fee fields; the choices remain the same across scenario presets.
- Replaced ambiguous Day1 UI labeling with a persistent Day2/local mock boundary. The page now explicitly says that preset tabs show saved examples, sliders only edit drafts, and neither calculation nor AI/API calls occur.
- Clarified that the stockout-risk control is a user cap input, not a computed probability; the probability-event definition remains pending the team's joint agreement.
- Marked Matrix values as prewritten/not computed and disclosed that a “Best fit” marker is still attached to the selected static preset after a draft change.
- Made the evidence entry points remain visible and distinguish quote matching from real-world/legal verification. Generic “Verified” wording for the local fixture bundle was removed.
- Added Day2 UX contract tests, neutral external-user testing tasks, a moderator script, invitation copy, severity guidance, and an empty feedback CSV template.

## Compatibility retained

No shared API or calculation contract was altered. The existing `schemaVersion` (`causora.contract.v1`), `dataVersion` (`demo-2026.10.04-v4`), `formulaVersion` (`tco-v1`), camelCase field names, units, scenario IDs, option IDs, and option definitions remain unchanged. No new fields were added to `MockData`, HTTP DTOs, or the frozen Golden Run. The npm package identity was advanced to `causora-day2@0.2.0` for archive identification only.

## Not implemented in Ding's scope

No 104-week calculation engine, contract PDF preprocessing, runtime quote matching, manual promotion to verified `BusinessVariable`, real `/api/simulate`, AI orchestration, or external supplier action is included. Those remain with their specified owners / later days. Changing shared calculation rules, scenario meanings, cash timing, stockout probability, or contract interpretation would require the three owners' joint agreement.

## External-user testing

The test plan and blank observation form are ready. They are **not evidence that a test took place**. Add participant roles, task observations, exact quotations, issues, and priorities only after real external participants have completed sessions.

## Final repair

Removed unused icon import; corrected case-sensitive test; split source tests from post-build HTTP test and added npm run check. Delivered newly generated static out, complete source, working Windows preview, source-linked intake wording and mock-only approval copy. Shared contracts, fixture values, Golden and other owners' modules are unchanged.

## P01 feedback revision
Larger Scenario Lab text, more spacing, plain-language choice titles and explicit Next action. Direct participant quote and unconfirmed Gemini analysis separated; retest pending.
