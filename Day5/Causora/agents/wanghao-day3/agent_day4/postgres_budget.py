"""Durable public-demo authorization, separate from prior local test grants.

One fixed ledger row is locked before reservation; missing/corrupt ledgers fail
closed. Provisioning is explicit, never performed by the serving process.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from .openrouter_provider import OpenRouterBudget, JOURNAL_KIND
from .provider import ProviderFailure

SCOPE = "public-day5-20261010"
CALL_CAP = 36
SUPPLEMENT_START = 26
SUPPLEMENT_USD = Decimal('0.10')


class PostgresBudget(OpenRouterBudget):
    durable_database = True

    def __init__(self, *, connection_url: str):
        super().__init__(journal_path=Path("DATABASE_ONLY_NOT_A_FILE"))
        self._connection_url = connection_url
        self._session_calls = 0

    def _locked_journal_transaction(self, action):
        try:
            import psycopg
            from psycopg.types.json import Jsonb
            with psycopg.connect(self._connection_url, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute("SET LOCAL lock_timeout = '5000ms'")
                    cur.execute("SET LOCAL statement_timeout = '7000ms'")
                    cur.execute("SELECT payload FROM causora_ai_budget WHERE id = %s FOR UPDATE", (SCOPE,))
                    row = cur.fetchone()
                    if row is None:
                        raise ProviderFailure("openrouter_budget_journal_unavailable")
                    journal = row[0]
                    if (not isinstance(journal, dict) or journal.get("kind") != JOURNAL_KIND
                            or journal.get("authorization") != {"scope": SCOPE, "maxCalls": CALL_CAP, "maxUsd": "1.00"}
                            or not isinstance(journal.get("entries"), list)):
                        raise ProviderFailure("openrouter_budget_journal_invalid")
                    for entry in journal["entries"]:
                        self._validated_entry(entry)
                    result, write = action(journal)
                    if write:
                        cur.execute("UPDATE causora_ai_budget SET payload=%s WHERE id=%s", (Jsonb(journal), SCOPE))
                    return result
        except ProviderFailure:
            raise
        except Exception:
            # Never propagate database URLs/passwords in transport or logs.
            raise ProviderFailure("openrouter_budget_journal_unavailable") from None

    def _reserve_persistently(self, entry, amount):
        if self._session_calls >= 6:
            raise ProviderFailure("provider_call_budget_exhausted")

        def action(journal):
            ceiling, _ = self._reconcile_metadata(journal)
            entries = journal["entries"]
            committed = self._journal_total(entries)
            if len(entries) >= CALL_CAP:
                raise ProviderFailure("provider_call_budget_exhausted")
            if self._journal_total(entries[SUPPLEMENT_START:]) + amount > SUPPLEMENT_USD:
                raise ProviderFailure("openrouter_supplement_budget_exhausted")
            if journal["metadata"].get("overCap") is True or committed + amount > ceiling:
                raise ProviderFailure("openrouter_usd_budget_exhausted")
            entries.append(entry)
            return (len(entries), committed + amount, ceiling), True

        result = self._locked_journal_transaction(action)
        self._session_calls += 1
        return result

    def set_journal_path(self, path):
        raise ProviderFailure("openrouter_budget_storage_switch_forbidden")

    def save_receipt(self, reservation_id, receipt):
        allowed = ('requestId', 'returnedModel', 'providerReturned', 'tokenUsage',
                   'usageCostUsd', 'outputSha256', 'requestSha256', 'status')
        def action(journal):
            entry = next((x for x in journal['entries'] if x['reservationId'] == reservation_id), None)
            if entry is None:
                raise ProviderFailure('openrouter_budget_journal_invalid')
            entry['providerReceipt'] = {key: receipt[key] for key in allowed if key in receipt}
            return None, True
        self._locked_journal_transaction(action)
