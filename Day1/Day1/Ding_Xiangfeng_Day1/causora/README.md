# Causora — Day 1 Product Prototype

> **Every claim carries a source. Every choice can be challenged.**

Causora is a decision-intelligence product concept that converts business evidence into inspectable decision variables, compares predefined choices under explicit scenarios, and keeps a human reviewer in control. This repository is the **Day 1 front-end baseline** from the Causora v3.0 Final Build Specification.

## What This Day 1 Prototype Delivers

The prototype uses local mock JSON to demonstrate the required Day 1 flow:

1. **Data Intake** — four downloadable synthetic files: 104-week demand CSV, 48-order delivery XLSX, opening-inventory CSV, and a six-page machine-readable agreement with all five evidence quotes on page 4.
2. **Scenario Lab** — quote-matched evidence becomes explicit Business Variables; mock scenario assumptions can be inspected and adjusted.
3. **Decision Matrix** — fixed D0, D1, and D2 options are compared under baseline, demand-drop, and lead-time-stress scenarios. Each mock cell has a five-line numeric TCO breakdown, versioned accounting convention, and cell-specific Formula Trace.
4. **AI Boardroom** — mock CFO, COO, and Risk perspectives are intentionally limited in scope; a Critic shows a cross-view compound risk.
5. **Decision Brief** — a predefined option is recommended through code-bound mock metric references, then a human can approve, reject, or change assumptions.

It also includes visible **loading**, **empty**, and **error** state previews for every stage, plus a local **CACHED · VERIFIED GOLDEN RUN** fallback containing an independently frozen complete mock snapshot. Changing inputs removes the Golden label. "Verified" refers to the local snapshot integrity checks, **not** a past successful live backend run.

The persistent **Proof Engine** makes the same document, variable, and matrix objects travel visually through all five stages. Its three perspective cards occupy separate tracks and its light paths appear only between cards, never across the readable data. It is an original, code-rendered composition—not a copied animation or a decorative 3D asset. A substantive **Decision Thread** below every stage provides source-backed context and next-step links without leaving large empty areas. Approve and Reject produce a short provenance-to-human animation and a stable local seal.

## Day 1 Scope Boundary

This is intentionally **not** a production decision system. It does **not** perform runtime PDF extraction/validation, simulation, Monte Carlo, LLM calls, persistence, authentication, or supplier action. All five evidence quotes were manually checked on page 4 of the bundled **synthetic** PDF, but the UI does not claim a live extraction engine. Values in the Matrix and Brief are local mock data that demonstrate the required UI/data contract only. Scenario presets select fixed mock rows; free slider adjustments are draft UI state and **do not recalculate** the Matrix. Brief deltas are derived from the selected preset mock rows, not from a simulation engine. **Approval is disabled while unsimulated draft assumptions are present.**

`API_CONTRACT.md` and `lib/contracts.ts` define a freezeable **proposal** for the Day 2 backend boundary, including units, errors and schema version. The next development stages will replace `demo_data/causora_day1_mock.json` with a deterministic simulation, Evidence Validator, Agent orchestration and runtime Numeric Guardrail after the three owners sign the interface. This ZIP is **not** full G1 sign-off.

## Run Locally

### Prerequisites

- Node.js **22.16 or newer in the 22 series** (see `.nvmrc`)
- npm

### Commands

```bash
npm ci
npm run dev
```

Then open `http://localhost:3000`.

The delivery ZIP also includes the validated static export in `out/`. To preview that exact production build without installing Node packages, run:

```bash
python3 -m http.server 3000 --directory out
```

Then open `http://localhost:3000`. Serve `out/` over HTTP rather than opening `index.html` with a `file://` URL.

Alternatively, after `npm ci && npm run build`, run **`npm start`**; unlike the previous ZIP, its start command now serves the static `out/` directory rather than calling incompatible `next start`. Set `PORT` and `HOST` if necessary. To self-host on a CDN or static host, publish **the contents of `out/` as the site root**, not the repository root. No API server is included. The Google Fonts used by the visual design load from an external service; local fallback fonts work if that service is blocked.

Synthetic source fixtures live in `public/demo/` (included in the static export) and may be regenerated with `python3 scripts/generate-demo-fixtures.py` after installing `reportlab` and `openpyxl`. The correspondence register is separately labelled synthetic; absence of an entry there is a **mock assumption**, not proof that a real party never sent notice.

Useful quality commands:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

## Project Map

```text
app/                    Next.js application shell and design system
components/             Workflow UI, stage views, controls, and trace dialogs
  proof-engine.tsx       Persistent evidence → variable → matrix visual narrative
  decision-moment.tsx    Human decision-gate animation and stable local seal
  context-deck.tsx       Substantive source-grounded content on every stage
demo_data/              Local Day 1 end-to-end mock contract
public/demo/            Four synthetic source files + synthetic notice register
golden/                 Complete frozen local mock snapshot with SHA-256
lib/contracts.ts        Shared API entity definitions and numeric units
lib/metrics.ts          Formatting, delta calculation and guarded text rendering
API_CONTRACT.md         Proposed Day 2 endpoint, request/response and error contract
FEEDBACK_RESPONSE.md    Point-by-point response to the 19-item external audit
scripts/                 Golden freeze, reproducible fixtures and static start server
out/                    Prebuilt static website (included in the delivery ZIP, not Git)
public/                 Manus route manifest
artifacts/              Responsive and decision screenshots, including proof-engine-fixed.png
tests/                  Static contract, visual wiring, and mock-data consistency checks
plan.md                 Approved implementation and design decisions
TODO.md                 Day 1 delivery outcomes
TESTING.md              Verification record and manual interaction script
```

## Core Decision Contract

| Object | Meaning in the prototype | Day 1 status |
| --- | --- | --- |
| Scenario | An external state, such as demand decline or lead-time pressure | Local mock, selectable |
| Decision Option | A predefined controllable choice: D0, D1, or D2 | Local mock, selectable |
| Constraint | A quote-matched contract field, such as the 60% minimum share | Local mock, traceable |
| Metric | A result produced by a future simulation engine | Mock deterministic display |
| Evidence | Source/page/quote reference for a contract value | Local mock, inspectable |

## Trust Design

The interface deliberately follows the specification's trust boundaries:

- A recommendation cannot invent a fourth option.
- The brief labels values as code-bound mock metrics rather than model-generated numbers.
- Evidence dialogs show source, page, matching method, quote, and a link to the actual synthetic source PDF. The Evidence stack lists all five records, including EV-019.
- The Boardroom separates CFO, COO, and Risk roles before the Critic introduces a compound-risk interpretation.
- Human actions are explicit and do not trigger an external side effect.
- An earlier approval is invalidated when the scenario, demand assumption, or risk threshold changes.
- Unsimulated slider drafts remain visible in the Brief and **block approval** until the preset inputs are restored.
- The selected scenario's Brief deltas are computed from the currently selected preset mock matrix, avoiding stale baseline numbers.
- The Golden Run is clearly identified as a cached local snapshot, is rendered from its own complete data copy and is immediately de-labelled when an input is edited.
- The v1 TCO trace uses base-price purchases plus a separate renewal premium **once**; all nine cells balance to the dollar.

## Accessibility and Responsive Behaviour

- Semantic navigation, stage labels, and buttons work with keyboard navigation.
- Focus states are visible across the interface.
- Evidence and Formula dialogs move focus inside, trap Tab/Shift+Tab, close with Escape and restore the invoking button's focus. The run-state badge remains visible on 390px phones.
- No meaning is conveyed by colour alone.
- `prefers-reduced-motion` reduces transitions and ambient motion.
- The desktop decision rail uses larger, higher-contrast stage titles and captions and remains visible while scrolling. At 830px and below it becomes a horizontal workflow navigator.
- Between 831px and 1199px, the dimensional scene gives way to three readable causal cards rather than compressing or overlapping the Matrix object; the same source/variable/matrix information remains available.

## Data, Privacy, and Disclaimer

All information in this repository is synthetic local mock data. Do not treat it as financial, legal, procurement, or professional advice. A production Causora build must disclose any third-party AI processing and must keep provider keys server-side.

## Day 1 Acceptance Snapshot

- [x] Five visible workflow stages in English
- [x] Local mock E2E data contract plus a proposed versioned backend API boundary
- [x] D0 / D1 / D2 × three scenarios
- [x] Five-entry Evidence stack, cell-specific Formula Trace, Boardroom, structured Critic, and Decision Brief UI
- [x] Human Approve / Reject / Change Assumptions controls
- [x] Loading, empty, error, and Golden Run experiences
- [x] Responsive and reduced-motion-aware interaction design
- [x] Persistent visual provenance, original depth, and human decision-gate motion
- [x] Data-grounded context on all five stages without large empty content areas
- [x] Build, lint, typecheck, test, and visual inspection records in `TESTING.md`

## What Day 1 Does Not Claim

The prototype does not claim live model reliability, real supplier notice verification, real simulation correctness, backend integration, live deployment resilience, Critic evaluation metrics, actual Day 2 participant bookings, or a completed Devpost submission. **Day 1 can be accepted as a mock baseline and interface draft, not as an unconditional complete G1 pass.** Those claims require the later Day 2–Day 7 work described in the Causora build specification.


## v4 delivery

This release corrects the external v3 audit. Read `V4_DELIVERY_NOTES.md` first. Shared API DTOs now distinguish selected/no-feasible results per scenario, and the v1 upload contract is synchronous. The runtime validates the complete bundled mock and Golden data before rendering; Golden activation also verifies SHA-256. Cost text follows increases/decreases, fractional percentage-point deltas preserve precision, and the Critic distinguishes the rolling-floor benchmark from total procurement excess. PDF/CSV/XLSX sources have correct MIME types under `npm start`.

State Studio includes a **No feasible option** preview with no winner and unavailable approval. This is a UI/API boundary fixture, not a backend computation. Existing sliders remain explicitly unsimulated drafts and block approval.

Run `npm run build` before `npm test` when working from a Git checkout without `out/`; the ZIP already includes it. The 21-test suite includes a real HTTP static-server check. Backend response adapters must validate the approved HTTP DTOs before use; the local `MockData` adapter represents a successful mock only.

`artifacts/history-v3/` contains old screenshots retained as labelled historical references. They do not prove v4 behavior. Current browser observations are recorded in `V4_DELIVERY_NOTES.md`. Source fixtures retain their original synthetic-document version because the underlying PDF/CSV/XLSX content did not change; the UI dataset version is `demo-2026.10.04-v4`.

No live deployment, backend, real simulator or participant booking is included. Team review/signatures and 2–3 confirmed participant slots are real human tasks, not software claims.
