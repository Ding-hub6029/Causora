# Wang Hao Day4 complete delivery

Start with FINAL_DELIVERY_REPORT.md. This complete owner project contains the preserved Ding Xiangfeng frontend baseline, Wang Hao AI module and adapter. Use DAY4_HANDOFF_TO_DENG.md for deliberate integration with Deng Jinzhu's separately modified backend.

Current verification: native Windows AI suite 294 passed. Backend 77 passed plus 37 subtests. Frontend typecheck/lint, 49 tests, build and one production smoke passed. Final-code fresh OpenRouter workflow passed with native Gemini Critic and GPT Synthesizer. No API key is included. Original human evidence and pending review/release flags remain intact.

## Local setup

Use Python 3.12 and Node 22. Install the agent/backend requirement files and frontend lockfile dependencies. Run python scripts/setup_day4.py --verify. Start python scripts/start_day4_backend.py. Explicit development mode is python scripts/start_day4_backend.py --development --port 8000. In frontend run npm ci and npm run dev:local. Configure documented backend URLs using frontend/.env.example.

Tests: python -m pytest -q in the agent/backend directories. Npm run check in frontend. Node scripts/test_frontend_boardroom_contract.mjs. Set NEXT_PUBLIC_CAUSORA_UNREVIEWED_DEV_MODE=UNREVIEWED_DEV_ONLY for node scripts/test_codex_development_contract.mjs. These tests do not send paid completions. Package check: python scripts/verify_day4_package.py.

Actual inference needs securely configured server credentials and explicit budget authorization. See OPENROUTER_INTEGRATION.md. Final fresh evidence is verification/wang_day4/codex_final_revision/final_accepted. Prior attempts remain history. Formal team/browser release and human approvals are not granted by individual module tests.
