# Causora Day 1 — Implementation Plan

## Scope

This project delivers **only the Day 1 front-end baseline** from the Causora v3.0 Final Build Specification. It is an English-language, interactive product prototype driven entirely by local mock data. No production backend, PDF processing, simulation engine, model provider, database, authentication, or external deployment is included.

The Golden Run must demonstrate this complete user-visible chain:

`Data Intake → Evidence & Variables → Scenario Lab → Decision Matrix → AI Boardroom → Decision Brief → Human Decision`

The product is deliberately opinionated: it presents traceable decision preparation rather than an autonomous AI answer. Every numerical card is explicitly labelled as code-bound mock data, every evidence statement has an identifier, and the final recommendation only references a predefined option.

## Product and Interaction Approach

### Design movement
**Editorial cybernetic command deck** — a restrained, high-trust interpretation of modern product motion design. It uses cinematic depth, progressive disclosure, and choreographed transitions without imitating the supplied reference videos.

### Core principles
1. **Traceability is visual:** evidence IDs, formula links, status chips, and a persistent decision trail make provenance visible instead of burying it in text.
2. **Motion communicates state:** page changes move along the decision sequence; feedback never exists merely as decoration.
3. **Sophistication through density with purpose:** deliberate negative space, precise typography, and one luminous accent frame meaningful evidence, comparisons, and decisions; no page has a large empty content area.
4. **Human authority is explicit:** recommendation and approval controls are visually distinct, preventing an AI suggestion from looking like an automated action.

### Color philosophy
A deep ink foundation suggests diligence and confidentiality. Pearl and glacier panels preserve readability. **Signal Lime (`#C8FF6B`)** is the ownable Causora action color, reserved for verified, ready, and approved states. Electric cobalt communicates computation; coral indicates a challenge or constraint.

### Layout paradigm
A **decision rail** anchors five stages at the left on desktop and becomes a horizontal progress navigator on compact screens. The main content is a layered canvas: a slim intelligence header, an asymmetric hero band, a central working surface, and contextual side intelligence. This avoids a generic centered-card dashboard while retaining clear task flow.

### Signature elements
- **Evidence thread:** a moving, fine-gradient route linking the active stage, trace references, and outcome.
- **Luminous data chambers:** translucent panels with subtle atmospheric gradients and reflection edges.
- **Decision pulse:** an animated live-status glyph that shifts from data intake to human decision as the sequence advances.

### Interaction and animation
- Framer Motion powers directional page transitions, staggered entries, shared status emphasis, and dialog presence.
- Stage navigation slides content horizontally according to workflow direction while respecting `prefers-reduced-motion`.
- Buttons use short spring feedback, never exaggerated bounce.
- Data cards reveal source meaning on focus/hover and remain fully keyboard operable.
- Toasts confirm human decisions; a visible reset restores the ordinary local mock. Open Golden Run explicitly to inspect its independent frozen snapshot.

### Typography system
- **Manrope** provides a compact, analytical interface voice.
- **DM Mono** marks evidence IDs, metrics, source tags, and computed values.
- Headline hierarchy uses high-contrast sizing and tight tracking; body text uses readable line height.

### Brand essence
**Causora turns evidence into inspectable business choices for teams that must defend every decision.**

Personality: **precise, composed, challenger-minded**.

Brand voice examples:
- “Every claim carries a source.”
- “A recommendation is ready for challenge.”

### Wordmark and mark
The wordmark pairs CAUSORA with an abstract split-orbit “C” mark: one evidence node and one decision node connected by a precise line. The mark is rendered with CSS/SVG-like geometry in the interface rather than a generic text-only logo.

### Reference-informed translation
The supplied motion references were analysed as interaction principles, not templates. Causora adopts their strongest transferable ideas: progressive reveal (summary before detail), shared-context transitions, precise hover/focus feedback, stable navigation, and content-sized detail overlays. It deliberately avoids unrelated decorative 3D scenes, liquid backgrounds, aggressive parallax, high-saturation marketing blocks, and copied layouts, visuals, or wording. Its original perspective-rendered Proof Engine is a functioning explanation of source → constraint → option, not scene decoration.

## Implementation Approach

### Day 1 visual-storytelling refinement

The second-pass experience introduces a persistent **Proof Engine** above the five stage views. Three code-rendered perspective stations embody the same objects throughout the flow: the document excerpt `EV-014`, the contract constraint `60 days / 60% / +14%`, and the D0–D2 option matrix. They occupy separate flex tracks rather than overlapping layers; the luminous connection travels only through the gutters, never across text. A travelling signal changes emphasis rather than replacing the entire illustration, so users see *evidence become a variable and then a comparison*. This is an original, data-specific visual system, not a copied 3D scene.

The opening frame is deliberately memorable: large editorial type is paired with a luminous, perspective-tilted proof engine that exposes real mock IDs and values. Its three labelled Evidence / Variable / Matrix controls navigate to the corresponding workflow stages. A subtle pointer-responsive tilt adds depth on capable devices, but all information is readable without pointer movement. At the final Brief, Approve or Reject triggers a short, stateful light-path resolution and a stable visible decision seal, not merely a toast. The persistent engine remains mounted across stages; Framer Motion interpolates geometry, emphasis and labels so transitions have shared context. Reduced-motion users see the same states without travelling animation.

Each stage adds a three-card **Decision Thread** tied to actual mock source IDs, selected scenario, metric cells or reviewer roles, so page density comes from decision content rather than ornamental filler. Data Intake places the dark input chamber next to its import register in one row and the source quote below: it does not stretch a mostly empty panel across unrelated rows. The Scenario sliders are explicitly labelled draft-only and do not imply a live simulation. The Brief derives its mock deltas from the currently selected scenario, invalidates an earlier human approval after edits, and blocks new approval until unsimulated drafts are restored to a preset.

- **Framework:** Next.js App Router, TypeScript, global CSS, Framer Motion, Lucide icons. The frontend is statically exported to `out/` for a runnable, backend-free ZIP preview; no public publication is implied.
- **Data:** `demo_data/causora_day1_mock.json` is the primary runtime mock source; `golden/golden_run.json` embeds a complete independent hashed snapshot. Both contain typed evidence, renewal dates and notice assumption, five Business Variables, D0/D1/D2, three scenarios, nine balanced mock metric cells, Boardroom/Critic and Brief. `public/demo/` supplies four inspectable synthetic inputs plus an explicit synthetic notice register. `API_CONTRACT.md` and `lib/contracts.ts` specify a proposed backend v1 boundary for Day 2 owner approval.
- **State:** client-side `useState` manages stage navigation, simulated loading/error/empty states, scenario selection, Golden Run visibility, formula trace, evidence detail, and human decision feedback.
- **Responsive strategy:** a legible, viewport-sticky desktop rail above 830px; a compact horizontal navigator at and below 830px. At 831–1199px, a readable three-card evidence projection replaces compressed perspective typography; 621–830px uses full-width cards; at and below 620px the projection becomes the compact mobile evidence chain. At 1200px and above the three dimensional stations retain real separation even at the narrowest perspective breakpoint. No critical interaction depends on hover.
- **Accessibility:** semantic page regions, keyboard-capable controls, labelled dialogs, visible focus rings, contrast-aware colours, and reduced-motion handling.
- **Quality evidence:** build, lint, type check, route-manifest verification, mock-flow browser smoke test, and a project self-audit record are included in the final ZIP.

## Project Structure

```text
causora/
├── app/
│   ├── globals.css                 # Design system, responsive rules, animation tokens
│   ├── layout.tsx                  # Metadata, font loading, application shell
│   └── page.tsx                    # Day 1 interactive decision-workflow prototype
├── components/
│   ├── app-shell.tsx               # Persistent rail, header, stage transitions
│   ├── proof-engine.tsx            # Persistent 3D evidence → variable → matrix narrative
│   ├── decision-moment.tsx         # Human approval/rejection sequence and stable seal
│   ├── context-deck.tsx            # Data-grounded content density for all five stages
│   ├── stage-views.tsx             # Five workflow stage views and empty/error/loading states
│   ├── detail-modal.tsx            # Complete evidence stack and cell-specific formula trace
│   └── ui.tsx                      # Reusable chips, panels and controls
├── demo_data/
│   ├── causora_day1_mock.json      # Typed mock E2E response used by all views
│   └── supplier_correspondence_log.csv # Synthetic notice assumption
├── golden/
│   └── golden_run.json             # Complete independent hashed local mock snapshot
├── lib/
│   ├── contracts.ts                # Shared cross-module v1 entities and units
│   └── metrics.ts                  # Code-computed deltas and numeric guardrail templates
├── public/
│   ├── demo/                       # Searchable 6-page PDF, CSV/XLSX/CSV + notice register
│   └── manus-routes.json           # Required route manifest
├── scripts/                        # Source fixture generation, Golden freeze, static server
├── tests/
│   └── day1-flow.test.mjs          # Static contract and mock-flow verification
├── .env.example                    # Safe, documented environment template
├── .nvmrc                          # Team Node version convention
├── README.md                       # English Day 1 handoff and run guide
├── API_CONTRACT.md                 # Proposed API endpoints, units, errors and validation
├── FEEDBACK_RESPONSE.md            # External audit remediation and remaining limits
├── TESTING.md                      # English verification record and QA actions
├── TODO.md                         # Day 1 implementation outcomes
└── plan.md                         # This approved plan
```

## Material Constraints

- All user-facing copy and project documentation are in English.
- The three decision options remain fixed: D0 Keep A, D1 Minimum A + Diversify B, D2 Exit A + Move to B.
- The Matrix is marked as a mock deterministic simulation. No simulated value is represented as a real production computation.
- Golden Run is local and clearly labelled `CACHED · VERIFIED GOLDEN RUN` whenever used.
- User controls do not make network requests or claim that a live model, PDF parser, or simulation engine has run.
