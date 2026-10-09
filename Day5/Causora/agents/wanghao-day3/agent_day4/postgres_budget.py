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
CALL_CAP = 58
SUPPLEMENT_START = 26
SUPPLEMENT_USD = Decimal('0.60')
SECOND_SUPPLEMENT_START = 34
SECOND_SUPPLEMENT_USD = Decimal('0.50')
THIRD_SUPPLEMENT_START = 42
THIRD_SUPPLEMENT_USD = Decimal('0.25')
BALANCE_AUTHORIZATION = {'scope': SCOPE, 'maxCalls': None, 'maxUsd': 'EXISTING_KEY_BALANCE', 'mode': 'existing_key_balance_no_topup'}


class PostgresBudget(OpenRouterBudget):
    durable_database = True

    def __init__(self, *, connection_url: str):
        super().__init__(journal_path=Path("DATABASE_ONLY_NOT_A_FILE"))
        self._connection_url = connection_url
        self._session_calls = 0
        self._session_reserved = Decimal('0')

    def configure_current_available(self, current_available):
        # Retain the six-call / one-dollar bound for each individual review.
        ceiling = super().configure_current_available(current_available)
        def action(journal):
            if journal.get('authorization') == BALANCE_AUTHORIZATION:
                self._reconcile_metadata(journal)
                return None, True
            return None, False
        self._locked_journal_transaction(action)
        return ceiling

    def _reconcile_metadata(self, journal):
        if journal.get('authorization') != BALANCE_AUTHORIZATION:
            return super()._reconcile_metadata(journal)
        metadata = journal.get('metadata')
        if not isinstance(metadata, dict):
            raise ProviderFailure('openrouter_budget_journal_invalid')
        captured = metadata.get('existingBalanceCeiling')
        if captured is None:
            if self.current_available_usd is None:
                raise ProviderFailure('openrouter_preflight_required')
            captured = self._journal_total(journal['entries']) + self.current_available_usd - self.margin_usd
            metadata['existingBalanceCeiling'] = str(captured)
            metadata['balanceAtActivationUsd'] = str(self.current_available_usd)
        try:
            ceiling = Decimal(str(captured))
        except Exception:
            raise ProviderFailure('openrouter_budget_journal_invalid') from None
        if not ceiling.is_finite() or ceiling <= 0:
            raise ProviderFailure('openrouter_budget_journal_invalid')
        if self.current_available_usd is not None:
            ceiling = min(ceiling, self._journal_total(journal['entries']) + self.current_available_usd - self.margin_usd)
            metadata['existingBalanceCeiling'] = str(ceiling)
        metadata['currentCeiling'] = str(ceiling)
        return ceiling, True

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
                            or journal.get("authorization") not in ({"scope": SCOPE, "maxCalls": CALL_CAP, "maxUsd": "1.00"}, BALANCE_AUTHORIZATION)
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
        if self._session_reserved + amount > self.max_usd:
            raise ProviderFailure('openrouter_usd_budget_exhausted')

        def action(journal):
            ceiling, _ = self._reconcile_metadata(journal)
            entries = journal["entries"]
            committed = self._journal_total(entries)
            balance_mode = journal.get('authorization') == BALANCE_AUTHORIZATION
            if not balance_mode and len(entries) >= CALL_CAP:
                raise ProviderFailure("provider_call_budget_exhausted")
            if not balance_mode and len(entries)>=SUPPLEMENT_START and self._journal_total(entries[SUPPLEMENT_START:]) + amount > SUPPLEMENT_USD:
                raise ProviderFailure("openrouter_supplement_budget_exhausted")
            if not balance_mode and len(entries)>=SECOND_SUPPLEMENT_START and self._journal_total(entries[SECOND_SUPPLEMENT_START:]) + amount > SECOND_SUPPLEMENT_USD:
                raise ProviderFailure("openrouter_supplement_budget_exhausted")
            if not balance_mode and len(entries)>=THIRD_SUPPLEMENT_START and self._journal_total(entries[THIRD_SUPPLEMENT_START:]) + amount > THIRD_SUPPLEMENT_USD:
                raise ProviderFailure("openrouter_supplement_budget_exhausted")
            if journal["metadata"].get("overCap") is True or committed + amount > ceiling:
                raise ProviderFailure("openrouter_usd_budget_exhausted")
            entries.append(entry)
            return (len(entries), committed + amount, ceiling), True

        result = self._locked_journal_transaction(action)
        self._session_calls += 1
        self._session_reserved += amount
        return result

    def require_complete_review_capacity(self):
        def action(journal):
            if journal.get('authorization') != BALANCE_AUTHORIZATION and CALL_CAP - len(journal['entries']) < 5:
                raise ProviderFailure('provider_call_budget_exhausted')
            return None, False
        self._locked_journal_transaction(action)

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
