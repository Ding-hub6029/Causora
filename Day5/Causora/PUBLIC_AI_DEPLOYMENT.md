# Public AI integration

Source integrates Wang Day5 safety fixes and a PostgreSQL transaction ledger. No key or database URL is shipped. Public scope public-day5-20261010 was separately authorized for 30 calls / USD 1 on 2026-10-10. Each pipeline remains capped at six calls; OpenRouter retries remain zero. Existing local grant receipts are retained separately, never reset.

Provisioning is an explicit operator step through deployment/provision_public_budget.py. The serving process never recreates missing ledgers. PostgreSQL SELECT FOR UPDATE serializes reservations, unknown costs remain reserved, failed storage refuses dispatch. Backend requires CAUSORA_AI_BUDGET_DATABASE_URL, OPENROUTER_API_KEY and existing approval flags.

Free Render Postgres expires 2026-11-09. Move durable ledger before expiration or disable AI. No paid hosting was purchased. Real deployment and browser acceptance results will be recorded separately after execution; this document does not assert they already passed.
