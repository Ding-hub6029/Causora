"""Explicit one-time provisioning; serving processes never recreate lost budgets."""
from pathlib import Path
import json
import os
import sys


def provision():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'agents' / 'wanghao-day3'))
    from agent_day4.postgres_budget import SCOPE, CALL_CAP
    from agent_day4.openrouter_provider import JOURNAL_KIND
    import psycopg
    from psycopg.types.json import Jsonb
    if os.getenv('CAUSORA_AI_BUDGET_PROVISION') != SCOPE:
        raise RuntimeError('Explicit provisioning scope required')
    try:
        with psycopg.connect(os.environ['CAUSORA_AI_BUDGET_DATABASE_URL'], connect_timeout=10) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS causora_ai_budget (id text PRIMARY KEY, payload jsonb NOT NULL)')
            payload = {'kind': JOURNAL_KIND, 'authorization': {'scope': SCOPE, 'maxCalls': CALL_CAP, 'maxUsd': '1.00'}, 'entries': []}
            conn.execute('INSERT INTO causora_ai_budget (id,payload) VALUES (%s,%s) ON CONFLICT (id) DO NOTHING', (SCOPE, Jsonb(payload)))
            conn.execute('CREATE TABLE IF NOT EXISTS causora_ai_prior_authorizations (id text PRIMARY KEY, payload jsonb NOT NULL)')
            history = json.loads((root / 'deployment' / 'prior_authorization_receipts.json').read_text())
            for name, record in history.items():
                conn.execute('INSERT INTO causora_ai_prior_authorizations (id,payload) VALUES (%s,%s) ON CONFLICT (id) DO NOTHING', (name, Jsonb(record)))
        print(f'Public budget provisioned: scope={SCOPE} maxCalls={CALL_CAP} maxUsd=1.00; prior grants preserved', flush=True)
    except Exception:
        raise RuntimeError('Public budget provisioning failed; no model dispatch') from None


if __name__ == '__main__':
    provision()
