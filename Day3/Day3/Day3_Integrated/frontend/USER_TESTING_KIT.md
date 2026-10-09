# Causora Day 2 — External User Test Kit

**Status: prepared, not conducted.** This package records no participant, consent, booked slot, session, observation, or feedback. The target is **2–3 people outside the build team**. A teammate's walkthrough is QA, not a substitute for external testing.

## 15-minute setup

- Use the Day2 local prototype and its synthetic fixtures only. Do not ask for confidential purchasing, supplier, or personal data.
- Ask permission to take notes. Use a participant code and a role/perspective (for example, procurement, operations, finance, analytics, or decision-maker) rather than collecting unnecessary identity details.
- Give a task, then observe quietly. Do not point to controls or define “scenario” and “option” before the participant explains their understanding. Record any assistance you provide.
- The opening should establish that this is a prototype using synthetic data and that no real supplier or business decision will be enacted. Do not coach the participant into the UI's intended explanation. Record whether the on-screen mock disclosures are noticed and understood.

## Copy-ready invitation

**Subject:** 15-minute usability test — Causora decision workspace prototype

Hi [Name],

I am testing an early prototype of Causora, a workspace for inspecting business evidence and comparing decision choices. Could you join a 15-minute session at [time option 1] or [time option 2]? No preparation is needed. I will ask you to try a few short tasks while thinking aloud. The prototype uses synthetic data and cannot enact a real supplier or business decision. With your permission, I will note your role/perspective and feedback. Please do not share confidential information.

Thank you,\
Ding Xiangfeng

## Participant tracker — leave blank until booked

| Participant code | Role / perspective | Session time | Consent to note feedback | Completed | Notes file |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |
|  |  |  |  |  |  |
|  |  |  |  |  |  |

## Moderator opening (about 45 seconds)

“Thanks for helping. This is an early prototype using synthetic data, not a production system. I am testing whether the product is clear, not testing you. Please think aloud. No real supplier or business action will happen. With your permission, I will take notes on your role/perspective and feedback. You can skip any task or stop at any time.”

## Core tasks (about 10 minutes)

1. **Scenario vs. option:** “Starting on Scenario Lab, tell me how you understand ‘scenario’ and ‘decision option’. Show me where you would go to change each one.” Do not explain the intended difference first.
2. **Demand and risk assumptions:** “Please explore what the interface offers for a lower-demand situation, then change the stockout-risk control.” Ask: “What did you expect to happen? What do you believe changed? What, if anything, would you check next?” Observe whether they notice the static-mock disclosure and whether they expect a recalculation.
3. **D0/D1/D2:** “Please compare the three choices and describe what each would mean for the business.” Note whether they distinguish decisions from external scenarios and find the allocation or contract detail.
4. **Contract evidence and recommendation:** “Show me how you would check the source for the renewal notice period or minimum purchase share. Then find the recommendation and anything you would use to judge it.” Observe whether source/page and formula/evidence links are discoverable and whether the recommendation reads as a saved mock or a real computed outcome.
5. **Change assumptions:** “If you wanted the result considered under a different assumption, show me what you would do.” Note if they find the path, change a control, notice draft/approval feedback, and understand that a changed input has not been simulated.

If time permits, ask the participant to return to the Brief and explain which parts they trust or would want verified before a real decision. Do not silently finish a task for them.

## Closing prompts

- What was clearest? What was least clear?
- Did the static/mock status and no-recalculation boundary make sense from the interface? What wording or visual cue helped—or failed to?
- Did you find the contract evidence without help? What more would you need to trust it?
- Did the recommendation feel like a real computed result, a saved example, or something else? Why?
- What single change would most improve this flow?

## Observation record

Record one row per important moment in `USER_TEST_FEEDBACK_DAY2.csv`: task, success/partial/stuck outcome, observed action, exact quote (verbatim. Otherwise mark `paraphrase`), help given, severity, likely cause, suggested change, owner, and whether a follow-up validated that change. Never turn a moderator interpretation into a participant quotation.

### Severity guide

- **High:** user cannot distinguish scenario from option, mistakes the mock for a real computation/action, cannot find material evidence, or cannot proceed.
- **Medium:** user succeeds with hesitation, misreads a risk/option detail, or needs a prompt.
- **Low:** polish issue that does not block understanding or completion.

## Prioritize after sessions

Rank issues by impact and frequency. Fix trust misunderstandings first, then blocked tasks, then repeated confusion. Add an evidence-backed change to the Day2 change log. Do not mark it user-validated until a participant completes a follow-up check.
