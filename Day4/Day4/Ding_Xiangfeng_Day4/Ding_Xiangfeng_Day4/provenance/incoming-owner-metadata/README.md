# Ding Xiangfeng Day 4 - complete development baseline

This is the complete source project with the accepted Day 1-3 baseline and Ding Xiangfeng's revised Day 4 frontend. No earlier ZIP is required. It can be used directly as Wang Hao and Deng Jinzhu's Day 4 development baseline and as the starting source tree for Ding's Day 5 work. Team G4 still awaits the teammates' Day 4 integrations.

## Find the right files

- frontend/: complete frontend source, unchanged dependencies and assets, and Ding's Day 4 changes.
- frontend/API_CONTRACT.md: interface shapes, required response headers, request correlation and CORS requirements.
- backend/backend/: existing FastAPI and Monte Carlo source. Deng's next changes can start here.
- agents/wanghao-day3/: existing Wang agent/review source. Wang's next changes can start here.
- TEAM_HANDOFF_DAY4.md: Day 4 integration responsibilities and the missing downstream services.
- API_CONTRACT_V2.md: existing shared v2 integration reference.
- release-pending/: original release/policy gates, retained as pending.
- DAY4_ACCEPTANCE_REPORT.md and DAY4_TEST_REPORT.md: Ding Day 4 scope and verification.
- verification/: Day 4 logs/screenshots and the independent recheck.
- PACKAGE_FILE_LIST.csv and MANIFEST.sha256: full package inventory and integrity checks.

## Run the frontend preview

Install Node.js 22 and npm. In the frontend directory run npm ci, then npm run dev:local. Open http://127.0.0.1:3000. Dependencies are installed locally. Node_modules and build output are intentionally not shipped. For a production preview run npm run build then npm start. Run npm run check for type checks, lint, automated tests, build and the production server test.

## Run the existing simulation backend

From backend/backend create and activate a Python virtual environment, install requirements.txt, and run python scripts/start_unreviewed_dev.py --host 127.0.0.1 --port 8000. In frontend copy .env.unreviewed-dev.example to .env.local, then start the frontend. See frontend/README.md for the full PowerShell commands. This explicit development mode is not decision-ready and preserves the approval gates.

## What still belongs to team Day 4 integration

Ding's frontend has been independently rechecked. Wang Hao and Deng Jinzhu have not yet delivered their Day 4 changes into this baseline. Actual reviewed Boardroom/Evidence routes, agent pipeline integration and team approval are not claimed complete. Follow TEAM_HANDOFF_DAY4.md before changing shared contracts. Do not bypass pending approvals. Day 5 work may start from this package, while any tasks depending on those services require their integration first.

## Necessary assets versus historical attachments

The unrelated planning document docs/Causora.pdf, obsolete frontend Day 1-3 reports and older integration screenshots have been removed. Runtime source PDFs, structured inputs, saved-example fixtures, tests, provenance and original human-review evidence remain because they are dependencies of the working project and its integrity checks. In particular frontend/public/demo/supplier_a_agreement.pdf is the source displayed by the Day 4 Evidence viewer. Deleting it would break that feature. The preserved original review evidence is not rewritten or presented as new Day 4 approval.

## Verification

The revised application code passed TypeScript, lint, 49 automated tests, production build and the static-server test. An independent browser check loaded page 4 of the source PDF and confirmed its exact-quote highlight. This packaging pass does not change application code or runtime data. All remaining manifests are recalculated for this full package. The older 933-entry figure in the audit record belongs to the unpruned revised input. This package uses its own current inventory.
