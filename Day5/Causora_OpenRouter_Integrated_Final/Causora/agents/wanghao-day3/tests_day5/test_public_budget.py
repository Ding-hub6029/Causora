import asyncio
import copy
import threading
from decimal import Decimal
import pytest
from agent_day4.postgres_budget import PostgresBudget, SCOPE, CALL_CAP
from agent_day4.openrouter_provider import JOURNAL_KIND
from agent_day4.provider import ProviderFailure


class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {'kind': JOURNAL_KIND, 'authorization': {'scope': SCOPE, 'maxCalls': CALL_CAP, 'maxUsd': '1.00'}, 'entries': []}

    def transact(self, action):
        with self.lock:
            candidate = copy.deepcopy(self.data)
            result, write = action(candidate)
            if write:
                self.data = candidate
            return result


def budget(store):
    value = PostgresBudget(connection_url='TEST_ONLY')
    value._locked_journal_transaction = store.transact
    value.configure_current_available(Decimal('10'))
    return value


def reserve(value, amount='0.001'):
    return asyncio.run(value.reserve(stage='TEST_ONLY', model='TEST_FIXTURE', amount=Decimal(amount), input_bound=1, max_output_tokens=1))


def test_global_cap_survives_new_sessions_and_unknown_cost():
    store = Store()
    for _ in range(5):
        instance = budget(store)
        for _ in range(6):
            reserve(instance)
    restored = budget(store)
    assert restored.snapshot()['callCount'] == 30
    assert restored.snapshot()['unknownCosts']['count'] == 30
    with pytest.raises(ProviderFailure, match='provider_call_budget_exhausted'):
        reserve(restored)


def test_one_pipeline_cannot_use_more_than_six():
    value = budget(Store())
    for _ in range(6):
        reserve(value)
    with pytest.raises(ProviderFailure, match='provider_call_budget_exhausted'):
        reserve(value)


def test_actual_cost_above_cap_poisoned_and_cannot_reset():
    store = Store()
    value = budget(store)
    identifier = reserve(value)
    asyncio.run(value.mark(identifier, 'returned', Decimal('1.01')))
    assert store.data['metadata']['overCap'] is True
    with pytest.raises(ProviderFailure, match='openrouter_usd_budget_exhausted'):
        reserve(budget(store))
    with pytest.raises(ProviderFailure, match='storage_switch_forbidden'):
        value.set_journal_path('other')
