# Causora Day 1 — Proof Engine and Motion Specification

## Design Thesis

**The source does not disappear when the recommendation appears.** Causora keeps three objects in view throughout the workflow: a quote-matched contract excerpt, its business-variable interpretation, and the predefined option matrix. The visitor sees a provenance path, not a generic dashboard transition or a decorative 3D scene.

## Opening Signature

- Editorial two-line headline: **From evidence / to a decision.**
- Three independent perspective stations, drawn with CSS and accurate mock labels rather than imported illustration assets; the card boxes never overlap.
- A path-length signal travels from source to variable to matrix through the **empty gutters** as stages advance. It never crosses a card's readable surface.
- A gentle pointer-responsive tilt adds dimensional depth on a mouse, but no information is hidden in hover.
- At 831–1199px and below 830px, a purpose-sized projection replaces tiny or cropped perspective text with three readable source/variable/matrix cards; the spatial scene is shown only at 1200px and above.

## Shared-Context Stage Motion

| Transition | Visible causal story | Source of truth |
| --- | --- | --- |
| Data Intake → Scenario Lab | The source plane yields emphasis to the contract-variable plane; the light path reaches the constraint. | `EV-014`, `EV-021`, `EV-024` and `demo_data/causora_day1_mock.json` |
| Scenario Lab → Decision Matrix | The matrix plane comes forward; D0/D1/D2 costs update when a mock scenario preset changes. | Selected `simulation.matrix[scenarioId]` numeric cells, formatted by code |
| Decision Matrix → AI Boardroom | The same matrix persists while the page introduces role-limited review and the Critic's compound-risk question. | `boardroom` and `critic` mock objects |
| AI Boardroom → Decision Brief | The visual chain remains available while the brief displays scenario-derived deltas. | Current scenario's D0 and D1 mock metric cells |
| Brief → Human decision | A five-node provenance route resolves into a human approval or rejection seal. | Reviewer click, stored only in local page state |

The Proof Engine is mounted **outside** the remounted stage canvas. Its elements change focus and position continuously rather than disappearing and reappearing between pages. Directional stage movement is deliberately short and never masks the user's next task.

## Motion Rules

1. Motion must clarify **provenance, state, or authority**, not exist as a novelty layer.
2. Keep the same typography, signal colour, and object meaning across the full five-stage sequence.
3. A new scenario preset updates only mock scenario-linked labels and values; a free slider adjustment is a visible **draft**, does not imply a calculation, and blocks approval until the preset controls are restored.
4. Human approval never triggers a network call. Changing the scenario or assumptions invalidates a previous approval. Editing Golden Run inputs removes its verified-snapshot badge before any new interpretation is shown.
5. Approve and Reject have distinct colour and seal outcomes, but the meaning is also written in text.
6. `prefers-reduced-motion` removes ambient animation, shortens Framer Motion transitions, and turns smooth scrolling into immediate positioning; the evidence path and controls remain available.

## Visual Vocabulary

- **Ink:** a private, analytical work surface.
- **Signal Lime:** a verified path and an explicit human affirmative action.
- **Aqua:** linked data and reviewed variables.
- **Coral:** a challenge, risk, or human rejection.
- **Manrope + DM Mono:** editorial decisions paired with inspectable identifiers.
- **Separated perspective stations:** evidence, constraint, matrix occupy distinct tracks with connector-safe gutters; never generic floating UI cards unrelated to data.

## Information Density Rule

Every page includes its stage-specific working surface and a three-part **Decision Thread** sourced from the mock data. The input chamber no longer stretches across two unrelated grid rows. The sticky decision rail has larger, higher-contrast labels and descriptions. Desktop (1440px), narrow desktop (1024px), tablet (768px), and mobile (390px) layouts were reviewed for blank regions, overlap, and legibility. Do not fill space with invented KPIs, fake simulation precision, or copied video-reference ornaments.

## Deliberate Non-Claims

The design shows a Day 1 **local mock UI contract**. It does not demonstrate PDF extraction, a live Monte Carlo engine, provider failover, real agent isolation, or a submitted purchase or contract decision. The decision seal is a local walkthrough state only.
