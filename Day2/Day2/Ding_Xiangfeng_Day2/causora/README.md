# Causora — Day 2 Front-End Prototype

**Release:** Day2 UI package `0.2.0`  
**Integration baseline:** v4.1  
**Primary owner:** Ding Xiangfeng  
**Mode:** Local interactive static mock; no backend or AI calls

> Every claim carries a source. Every choice can be challenged.

This package preserves the original Day1 archive and uses a separate Day2 copy of Ding Xiangfeng's v4.1 front end. Day2 focuses on the Scenario Lab mock UI, clear scenario-versus-option language, visible calculation limits, and preparation for the first external-user test.

## Day2 changes

- Scenario Lab explains that a **scenario** is an external condition and D0/D1/D2 are **business choices**. The three unchanged option definitions and allocations are visible beside the scenario controls.
- A Day2/static-mock notice states that preset tabs show prewritten examples and sliders only edit draft assumptions: **no simulation, AI, or HTTP request runs, and Matrix values do not recalculate**.
- The risk control is called a cap; the exact stockout-probability definition is explicitly pending joint team agreement before the engine is implemented.
- Matrix and Brief disclose saved-mock status. Draft assumptions and stale “Best fit” labels are not presented as recalculated; approval remains unavailable while draft inputs are present.
- The fixture bundle no longer uses a generic “Verified” label. Evidence remains clickable by source ID, and quote matching is distinguished from legal or real-world verification.
- `USER_TESTING_KIT.md` contains neutral external-user tasks, a moderator script, a copy-ready invitation, and a blank tracker. `USER_TEST_FEEDBACK_DAY2.csv` is intentionally empty until real sessions happen.

## Run locally

Prerequisites: Node.js `22.16.x` (see `.nvmrc`) and npm.

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`.

Run quality checks from the project root:

```bash
npm run typecheck
npm run lint
npm test
npm run build
npm run test:production
```

A successful `npm run build` generates the static export in `out/`. Run `npm start` to serve that generated export locally. To publish on a static host, publish the **contents** of `out/` as the site root; this repository does not include an API server. This delivery includes a freshly rebuilt Day2 `out/` export. Run `START_PREVIEW.cmd` on Windows or `npm start` with Node.js 22 to preview without installing dependencies. Run `npm ci` followed by `npm run check` to reproduce all source and production checks. External Google Fonts may fall back to system fonts if blocked.

## Mock, data, and integration boundary

- All evidence, notices, and business inputs in `demo_data/` and `public/demo/` are synthetic demonstration fixtures. A quote match is not legal review, and a mock notice register is not proof that notice was or was not sent in real life.
- Preset Matrix and Brief metrics are saved Day1 mock values, not outputs of a deterministic 104-week engine or a Monte Carlo run. Slider values do not alter these results.
- The UI makes no `/api/simulate` call and does not claim Day3 AI orchestration.
- The shared schema remains `causora.contract.v1`; the frozen fixture remains `demo-2026.10.04-v4`; the formula label remains `tco-v1`. Scenario IDs, field names, units, and D0/D1/D2 meanings are unchanged. Only the npm package name/version identifies this Day2 front-end archive.
- This is Ding's frontend work only. **It is not a team G2 sign-off.** G2 also depends on Deng Jinzhu's deterministic matrix engine and Wang Hao's evidence/contract-field work being integrated and validated.

## External-user testing status

The test plan is prepared; **one participant’s direct readability/terminology feedback is recorded in USER_FEEDBACK_RESPONSE_DAY2.md; full task observations and revision retest are not recorded**. Arrange 2–3 participants outside the build team, obtain consent to note feedback, run the tasks in `USER_TESTING_KIT.md`, and fill the CSV only with actual observations. Team self-review is not a substitute for this study.

See `DAY2_CHANGELOG.md`, `DAY2_TEAM_STATUS.md`, and `DAY2_TEST_REPORT.md` for scope and verification status.

## Architecture and ownership

Next.js/React renders a validated local MockData snapshot; lib/validation checks versions, accounting and Golden integrity; lib/metrics derives deltas; five stages share one state. Evidence links to synthetic source files. No runtime LLM or backend call is made. Source values and displayed costs are illustrative, not financial/legal guidance. Wang owns evidence extraction and review; Jinzhu owns simulation and oracle; Ding owns UI/integration. Existing draft API schemas remain authoritative until an agreed versioned change. Real source evidence, calculations, independent oracle comparison and provider reliability must be tested before production claims.

## Verification and completion

25 tests and production build passed in this Windows repair. See DAY2_TEST_REPORT.md. Direct P01 feedback and the corresponding revisions are documented; structured task observations and retest remain pending. Final README evaluation numbers, production deployment and real provider results belong to later gates. Archived Day1/V4 notes are historical references.
