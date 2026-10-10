# Day 5 Changelog — Ding Xiangfeng

## Added

- Bundled the genuine frozen verified E2E record at `frontend/public/golden/verified_golden_e2e.json`. The browser loads it from a fixed same-origin asset path when local storage is empty or invalid, then uses the existing production validators before showing a Golden replay.
- Added an explicit static-only public build mode. It identifies the backend as not configured, does not issue a health request, and offers the verified read-only Golden fallback without implying Live Simulation or a fresh AI review.
- Added a server-side static-only proxy gate in `frontend/scripts/serve-static.mjs`: `/health` and `/api/*` return a no-store `503 backend_not_configured` response and do not forward to a localhost upstream. Production tests verify that the configured test upstream receives zero requests.
- Added clear provenance for the frozen automated `Rejected` browser-test artifact and removed controls that could make the snapshot look like a human/team decision.
- Bound cached ProofEngine evidence and policy-input cards to the revalidated Golden records, not the separate Day 2 demo fixtures. Cached Boardroom and Brief labels now make the absence of live AI/API calls explicit.
- Added a short second-user-test task and feedback form, deployment/run instructions, package verification record, public-browser screenshots, and a Day5 SHA-256 inventory.

## Fixed during Day 5 owner-side QA

- A clean public browser exposed a snapshot provenance mismatch in ProofEngine. The snapshot view now renders the actual validated Golden Evidence and stored policy input records. The fix was verified in the public preview and is not represented as participant feedback.
- The static-only server now fails closed for direct `/health` and `/api/*` requests rather than relying only on the frontend not to call them.

## Preserved

- Matrix + Trace v2 schema, run IDs, dataVersion, seeds, option/scenario definitions, metrics, units, and validation rules.
- All 15 approved assumptions and the distinction between the 1,200-unit synthetic opening-inventory bridge and 1,840 observed CSV units.
- Existing approvals, AI usage/security gates, release files, and pending human/team decisions.
- Deng Jinzhu's simulation/service ownership and Wang Hao's AI/Critic ownership. Their Day 5 work is not implemented or scored here.

## Validation snapshot

- `npm run check`: typecheck and lint passed, 55 frontend tests passed, production build passed, and three production-server tests passed.
- `npm audit --omit=dev`: zero production dependency vulnerabilities; the full install audit still reports five high-severity findings in the complete (including development) dependency tree.
- Public fresh-context browser run: 11 acceptance checks pass after static-only route-gate verification; five evidence screenshots are retained. No public API calls or console errors occurred during normal page interaction.
- Genuine user test and feedback-driven fix: **pending real participants**.
