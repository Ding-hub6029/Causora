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
    for _ in range(CALL_CAP // 6):
        instance = budget(store)
        for _ in range(6):
            reserve(instance)
    restored = budget(store)
    assert restored.snapshot()['callCount'] == CALL_CAP
    assert restored.snapshot()['unknownCosts']['count'] == CALL_CAP
    with pytest.raises(ProviderFailure, match='provider_call_budget_exhausted'):
        reserve(restored)


def test_one_pipeline_cannot_use_more_than_six():
    value = budget(Store())
    for _ in range(6):
        reserve(value)
    with pytest.raises(ProviderFailure, match='provider_call_budget_exhausted'):
        reserve(value)

def test_supplemental_spend_cap_remains_independent_of_original_dollar():
    store=Store()
    for _ in range(4):
        instance=budget(store)
        for _ in range(6):reserve(instance)
    instance=budget(store)
    reserve(instance);reserve(instance)
    reserve(instance,'0.60')
    with pytest.raises(ProviderFailure,match='supplement_budget_exhausted'):
        reserve(instance)

def test_second_supplement_has_its_own_quarter_dollar_cap():
    store=Store()
    for _ in range(5):
        instance=budget(store)
        for _ in range(6):reserve(instance)
    instance=budget(store)
    for _ in range(4):reserve(instance)
    instance=budget(store)
    reserve(instance,'0.50')
    with pytest.raises(ProviderFailure,match='supplement_budget_exhausted'):
        reserve(instance)


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

def test_complete_review_preflight_blocks_partial_spend():
    store = Store()
    for count in range(CALL_CAP - 4):
        if count % 6 == 0:
            instance = budget(store)
        reserve(instance)
    before = copy.deepcopy(store.data)
    with pytest.raises(ProviderFailure, match='provider_call_budget_exhausted'):
        budget(store).require_complete_review_capacity()
    assert store.data == before

def test_third_supplement_has_independent_cap():
    store = Store()
    for count in range(42):
        if count % 6 == 0:
            instance = budget(store)
        reserve(instance)
    instance = budget(store)
    reserve(instance, '0.25')
    with pytest.raises(ProviderFailure, match='supplement_budget_exhausted'):
        reserve(instance)

