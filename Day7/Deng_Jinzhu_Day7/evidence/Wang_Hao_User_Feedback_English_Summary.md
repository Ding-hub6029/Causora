# Wang Hao - Historical User Feedback, English Summary

This is an abridged English translation of the supplied Chinese participant record, not a new test or a verbatim English transcript. The original remains outside these English delivery packages. No additional participant is claimed.

Participant: Wang Hao, project team member with some prior project and business-context familiarity. Date: 2026-10-10. Desktop: Sandbox browser. Mobile: Android portrait, screenshot time 02:53. Original deployment 485b2c2, retest 4da7c5f.

## Recorded observations

1. Purpose: a supplier-decision tool that connects contract evidence, variables and option comparisons. The participant initially expected a direct recommendation, then recognized the emphasis on the decision trail. Supplier A's base price was USD 12.00, B's USD 12.60.
2. Evidence: four inputs included demand history, delivery records, opening inventory and a six-page machine-readable Supplier A PDF. EV-014 pointed to page 4 and the 60-day notice clause. The participant distinguished source evidence from the 60-day, 60% and 14% parameters, but found renewal lock-in and minimum-share terminology initially confusing.
3. Scenarios versus choices: Baseline, Demand -15%, Cash stress and Lead-time stress described external conditions. D0 kept A, D1 retained A's minimum and introduced B, D2 moved to B. Slider edits changed draft assumptions and required a fresh simulation. This was not initially obvious.
4. Baseline live simulation succeeded after service wake-up, approximately 15 seconds after clicking Run simulation. 1,000 runs, seed 1042026. D0: TCO 365,811, stockout 92%, P90 369,631. D1: 348,040, 1%, 348,723. D2: 356,665, 90%, 361,811. D1 selected. LIVE API / 104 WEEKS and validated response displayed. Request req-53ca59a970664da4a54245f4e5b1b4bb. Earlier failure belonged to the old version.
5. Formula Trace: D1 procurement 318,240, holding 3,590, shortage loss 2, renewal 26,208 and exit 0 reconciled to 348,040. P90 needed a clearer explanation than TCO. The participant understood it as greater cash-outflow pressure rather than the mean.
6. Golden Evidence EV-014, EV-019, EV-020 and EV-024 shared one simulation identity and traced contract parameters to the source. Users who only read results might miss this relationship.
7. Boardroom waiting remained distinct from a successful live simulation. Historical cached reviews were visible separately and were not attached to a new run. The simultaneous cached content and unavailable/waiting status initially appeared contradictory.
8. Demand -15% live retest succeeded in approximately 15 seconds. D0: TCO 310,547, stockout 26%, P90 316,020. D1: 358,161, 0%, 358,829. D2: 306,401, 96%, 312,919. D1 selected. Request req-3778f68ad0c3461f83f94028dd255b02, scenario demand-drop. Boardroom waited for a matching review rather than reusing Baseline.
9. Verified cache was understood as a validated, fixed, read-only snapshot without a new API or AI call. Live computation validated new assumptions. Both modes were observed.
10. Android portrait loaded correctly, with readable cards and usable health controls. Navigation required horizontal scrolling and the rightmost item was partially clipped. The participant requested a clearer scroll cue. Sliders, Formula Trace modal and the entire Matrix were not comprehensively mobile-tested. No major mistaken clicks were recorded.

## Durations and improvement priorities

Tasks 1-3: about 2, 3 and 4 minutes. Task 4: service wake-up plus about 15 seconds for simulation. Tasks 5-7: about 5, 3 and 4 minutes. Task 8: about 15 seconds after editing. Tasks 9-10: about 3 and 5 minutes.

P1: distinguish live failure, saved example and verified cache. Separate live Boardroom status from historical cached results. P2: explain P90, clarify terminology and improve mobile navigation affordance. The participant suggested Chinese explanations in the historical feedback. This English package does not add that product feature.

The participant confirmed the historical record and retest distinctions. Baseline and Demand -15% succeeded on 4da7c5f. Matching Boardroom still awaited execution. Mobile basic loading and reading passed, with additional interactions pending. This is historical user evidence, not current-release acceptance or independently unseen evaluation.
