"""OpenRouter integration tests: local fakes only, never real credentials or HTTP."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import types
from decimal import Decimal
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = PROJECT_ROOT / "agents" / "wanghao-day3"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from agent_day4.openrouter_provider import (
    CRITIC_MODEL,
    PRIMARY_MODEL,
    MODELS,
    OpenRouterBudget,
    OpenRouterProvider,
    OpenRouterSession,
)
from agent_day4.provider import ProviderFailure, providers_from_env
from agent_day4.wire import PipelineConfig


class APITimeoutError(Exception):
    pass


class FakeCompletions:
    def __init__(self, owner):
        self.owner = owner

    async def create(self, **parameters):
        self.owner.create_calls.append(parameters)
        if self.owner.error is not None:
            raise self.owner.error
        return self.owner.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response or types.SimpleNamespace(
            id="chat-local-1",
            model=PRIMARY_MODEL,
            provider="local-test-provider",
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"ok":true}'))],
            usage=None,
        )
        self.error = error
        self.create_calls: list[dict] = []
        self.with_options_calls: list[dict] = []
        self.closed = False
        self.chat = types.SimpleNamespace(completions=FakeCompletions(self))

    def with_options(self, **kwargs):
        self.with_options_calls.append(kwargs)
        return self

    async def close(self):
        self.closed = True


def model_document(*, missing=None, omit_parameter=None):
    rows = []
    for model_id, spec in MODELS.items():
        if model_id == missing:
            continue
        parameters = {"response_format", "structured_outputs", "reasoning", "max_tokens"}
        if spec.needs_max_completion_tokens:
            parameters.add("max_completion_tokens")
        if model_id == omit_parameter[0] if omit_parameter else False:
            parameters.remove(omit_parameter[1])
        rows.append({"id": model_id, "supported_parameters": sorted(parameters),"pricing":{'prompt':str(spec.prompt_usd_per_token),'completion':str(spec.completion_usd_per_token)}})
    return {"data": rows}


def key_document(**overrides):
    data = {
        "limit": "1",
        "usage": "0",
        "limit_remaining": "1",
        "limit_reset": None,
        "include_byok_in_limit": True,
    }
    data.update(overrides)
    return {"data": data}


def session_with_fake(*, client=None, models=None, key=None, budget=None):
    async def fake_get(path):
        if path == "/models":
            return models if models is not None else model_document()
        if path == "/key":
            return key if key is not None else key_document()
        raise AssertionError("unexpected local route")

    config = PipelineConfig(retries=0, max_calls=6)
    return OpenRouterSession(
        api_key="unit-test-not-a-real-key",
        config=config,
        client=client or FakeClient(),
        http_get=fake_get,
        budget=budget,
    )


async def authorized_session(**kwargs):
    session = session_with_fake(**kwargs)
    await session.preflight()
    session.authorize(fresh_dedicated_key_confirmed=True)
    return session


async def complete(provider, *, stage="CFO", timeout=7.25):
    return await provider.complete(
        stage=stage,
        payload={"local": "fake"},
        schema={"type": "object", "properties": {"ok": {"type": "boolean"}}, "required": ["ok"], "additionalProperties": False},
        system="local fake system",
        request_timeout=timeout,
    )


def test_only_approved_full_model_ids_and_families_are_accepted():
    session = session_with_fake()
    assert OpenRouterProvider(PRIMARY_MODEL, session=session).family == "openai-gpt"
    assert OpenRouterProvider(CRITIC_MODEL, session=session).family == "google-gemini"
    with pytest.raises(ProviderFailure, match="openrouter_model_not_allowed"):
        OpenRouterProvider("gpt-5-mini", session=session)
    with pytest.raises(ProviderFailure, match="openrouter_model_not_allowed"):
        OpenRouterProvider("google/gemini-3-pro", session=session)


def test_openrouter_cannot_fallback_to_manus_credentials(monkeypatch):
    for name in (
        "OPENROUTER_API_KEY", "CAUSORA_PRIMARY_MODEL", "CAUSORA_GEMINI_CRITIC_MODEL",
        "CAUSORA_FALLBACK_CRITIC_MODEL", "CAUSORA_AI_MAX_CALLS", "CAUSORA_AI_PIPELINE_CALLS", "CAUSORA_AI_RETRIES",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CAUSORA_AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENAI_API_KEY", "manus-key-must-not-be-read")
    monkeypatch.setenv("OPENAI_API_BASE", "https://manus.invalid/v1")
    with pytest.raises(ProviderFailure, match="openrouter_not_configured"):
        providers_from_env()


def test_explicit_openrouter_factory_forces_six_calls_zero_retries_and_full_ids(monkeypatch):
    class FakeAsyncOpenAI(FakeClient):
        def __init__(self, **kwargs):
            super().__init__()
            self.kwargs = kwargs

    fake_openai = types.ModuleType("openai")
    fake_openai.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("CAUSORA_AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "unit-test-not-a-real-key")
    for name in ("CAUSORA_PRIMARY_MODEL", "CAUSORA_GEMINI_CRITIC_MODEL", "CAUSORA_FALLBACK_CRITIC_MODEL", "CAUSORA_AI_MAX_CALLS", "CAUSORA_AI_PIPELINE_CALLS", "CAUSORA_AI_RETRIES"):
        monkeypatch.delenv(name, raising=False)
    primary, critic, fallback, config = providers_from_env()
    try:
        assert (primary.model, critic.model, fallback.model) == (PRIMARY_MODEL, CRITIC_MODEL, PRIMARY_MODEL)
        assert primary.budget is critic.budget is fallback.budget
        assert (config.retries, config.max_calls, primary.budget.limit) == (0, 6, 6)
        assert primary.kind == critic.kind == fallback.kind == "LIVE_PROVIDER"
        assert primary.session.client.kwargs["max_retries"] == 0
        assert primary.session.client.kwargs["base_url"] == "https://openrouter.ai/api/v1"
    finally:
        asyncio.run(primary.aclose())


@pytest.mark.parametrize(
    ("models", "key", "reason"),
    [
        (model_document(missing=CRITIC_MODEL), None, "openrouter_model_not_available"),
        (model_document(omit_parameter=(PRIMARY_MODEL, "structured_outputs")), None, "openrouter_model_unsupported"),
        (None, key_document(limit=None), "openrouter_key_limit_invalid"),
        (None, key_document(limit="1.01", limit_remaining="1.00"), "openrouter_key_limit_invalid"),
        (None, key_document(limit_reset="monthly"), "openrouter_key_limit_reset_not_null"),
        (None, {"data": {"limit": "1"}}, "openrouter_key_limit_missing"),
    ],
)
def test_preflight_rejects_invalid_models_or_key_limit_before_any_dispatch(models, key, reason):
    client = FakeClient()
    session = session_with_fake(client=client, models=models, key=key)

    async def check():
        with pytest.raises(ProviderFailure, match=reason):
            await session.preflight()
        provider = OpenRouterProvider(PRIMARY_MODEL, session=session)
        with pytest.raises(ProviderFailure):
            await complete(provider)
        assert client.create_calls == []

    asyncio.run(check())


def test_preflight_requires_authorization_before_paid_dispatch():
    client = FakeClient()
    session = session_with_fake(client=client)

    async def check():
        await session.preflight()
        provider = OpenRouterProvider(PRIMARY_MODEL, session=session)
        with pytest.raises(ProviderFailure, match="openrouter_paid_dispatch_not_authorized"):
            await complete(provider)
        assert client.create_calls == []

    asyncio.run(check())


def test_preflight_accepts_historical_usage_and_remaining_credit_above_usd_one():
    session = session_with_fake(key=key_document(limit="10", usage="8.88036651", limit_remaining="1.11963349", include_byok_in_limit=False))

    async def check():
        summary = await session.preflight()
        assert summary["budget"] == {
            "authorizedUsd": "1.00",
            "currentAvailableUsd": "1.11963349",
            "safetyMarginUsd": "0.05",
            "currentCeilingUsd": "0.95",
        }
        assert session.budget.max_usd == Decimal("0.95")
        assert summary["key"] == {
            "limitUsd": "10",
            "usageUsd": "8.88036651",
            "limitRemainingUsd": "1.11963349",
            "limitReset": None,
            "includeByokInLimit": False,
            "byokCostAccounting": "NOT_INCLUDED_IN_KEY_LIMIT; NO_BYOK_PARAMETERS_OR_KEYS_ARE_PERMITTED",
        }

    asyncio.run(check())


def test_strict_schema_mapping_reasoning_and_exact_sdk_timeout_are_local_only():
    client = FakeClient()

    async def check():
        session = await authorized_session(client=client)
        gpt = OpenRouterProvider(PRIMARY_MODEL, session=session)
        assert await complete(gpt, stage="CFO", timeout=7.25) == {"ok": True}
        gpt_request = client.create_calls[-1]
        assert client.with_options_calls[-1] == {"timeout": 7.25}
        assert gpt_request["model"] == PRIMARY_MODEL
        assert gpt_request["max_tokens"] == 2048
        assert gpt_request["response_format"]["json_schema"]["strict"] is True
        assert gpt_request["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
        assert "tools" not in gpt_request
        assert gpt_request["extra_body"] == {
            "provider": {"require_parameters": True, "allow_fallbacks": False, "max_price": {"prompt": 0.25, "completion": 2.0}},
            "reasoning": {"effort": "minimal"},
            "plugins": [],
        }
        assert gpt.audit[-1]["source"] == "OPENROUTER_HTTPS_API"
        assert gpt.audit[-1]["exactSdkDeadlineSeconds"] == 7.25

        client.response = types.SimpleNamespace(
            id="chat-local-gemini", model=CRITIC_MODEL, provider=None,
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"ok":true}'))], usage=None,
        )
        gemini = OpenRouterProvider(CRITIC_MODEL, session=session)
        await complete(gemini, stage="Critic", timeout=14.5)
        gemini_request = client.create_calls[-1]
        assert gemini_request["response_format"] == {"type": "json_object"}
        assert "Include every required property" in gemini_request["messages"][0]["content"]
        assert '"additionalProperties":false' in gemini_request["messages"][0]["content"]
        assert gemini_request["max_tokens"] == 4096
        assert gemini_request["extra_body"]["reasoning"] == {"effort": "low"}
        assert "thinking" not in json.dumps(gemini_request)
        assert "max_tokens" not in gemini_request["extra_body"]["reasoning"]
        assert gemini.audit[-1]["returnedModel"] == CRITIC_MODEL

    asyncio.run(check())


def test_atomic_budget_race_cannot_exceed_usd_cap_or_six_calls():
    budget = OpenRouterBudget(max_usd=Decimal("1.00"))

    async def check():
        results = await asyncio.gather(
            *(budget.reserve(stage="CFO", model=PRIMARY_MODEL, amount=Decimal("0.51"), input_bound=1, max_output_tokens=1) for _ in range(8)),
            return_exceptions=True,
        )
        assert budget.used == 1
        assert budget.reserved_usd == Decimal("0.51")
        assert sum(isinstance(result, ProviderFailure) for result in results) == 7

    asyncio.run(check())


def test_excess_request_is_rejected_before_fake_sdk_dispatch():
    client = FakeClient()
    budget = OpenRouterBudget(max_usd=Decimal("0.000001"))

    async def check():
        session = await authorized_session(client=client, budget=budget)
        provider = OpenRouterProvider(PRIMARY_MODEL, session=session)
        with pytest.raises(ProviderFailure, match="openrouter_usd_budget_exhausted"):
            await complete(provider)
        assert client.create_calls == []
        assert budget.used == 0

    asyncio.run(check())


def test_timeout_keeps_maximum_reservation_instead_of_releasing_it():
    client = FakeClient(error=APITimeoutError())

    async def check():
        session = await authorized_session(client=client)
        provider = OpenRouterProvider(PRIMARY_MODEL, session=session)
        with pytest.raises(ProviderFailure, match="provider_timeout"):
            await complete(provider)
        assert provider.budget.used == 1
        assert provider.budget.reserved_usd > 0
        assert provider.audit[-1]["status"] == "provider_timeout"
        assert provider.audit[-1]["usageCostStatus"] == "Unverified"

    asyncio.run(check())


def test_secret_looking_model_output_is_rejected_and_not_retained():
    secret_like = "sk-or-v1-" + "a" * 24
    client = FakeClient(response=types.SimpleNamespace(
        id="chat-local-secret", model=PRIMARY_MODEL, provider=None,
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=json.dumps({"value": secret_like})))], usage=None,
    ))

    async def check():
        session = await authorized_session(client=client)
        provider = OpenRouterProvider(PRIMARY_MODEL, session=session)
        with pytest.raises(ProviderFailure, match="provider_secret_output_rejected"):
            await complete(provider)
        record = provider.audit[-1]
        assert record["status"] == "provider_secret_output_rejected"
        assert "rawParsedOutput" not in record and "parsedOutput" not in record
        assert secret_like not in json.dumps(record)

    asyncio.run(check())


def test_request_size_guard_rejects_without_truncating_or_dispatching():
    client = FakeClient()

    async def check():
        session = await authorized_session(client=client)
        provider = OpenRouterProvider(PRIMARY_MODEL, session=session)
        with pytest.raises(ProviderFailure, match="openrouter_request_too_large"):
            await provider.complete(
                stage="CFO", payload={"facts": "x" * 24_001}, schema={"type": "object"}, system="s", request_timeout=1,
            )
        assert client.create_calls == []

    asyncio.run(check())

@pytest.mark.parametrize('bad_price',[None,'invalid','NaN','0.5'])
def test_live_price_is_checked_not_only_static_request_ceiling(bad_price):
    models=model_document();models['data'][0]['pricing']['prompt']=bad_price
    session=session_with_fake(models=models)
    with pytest.raises(ProviderFailure):asyncio.run(session.preflight())
    assert session.client.create_calls==[]


def test_remaining_credit_tightens_shared_budget_after_safety_margin_before_dispatch():
    session=session_with_fake(key=key_document(limit='10',usage='9.94',limit_remaining='.06'))
    asyncio.run(session.preflight())
    assert session.budget.max_usd==Decimal('.01')


def test_remaining_credit_at_or_below_safety_margin_rejects_preflight():
    session=session_with_fake(key=key_document(limit='10',usage='9.95',limit_remaining='.05'))
    with pytest.raises(ProviderFailure,match='openrouter_available_budget_too_small'):
        asyncio.run(session.preflight())


def test_empty_content_still_records_verified_usage_cost():
    response=types.SimpleNamespace(id='local-empty',model=PRIMARY_MODEL,provider='local-test-provider',
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=''))],usage={'prompt_tokens':12,'completion_tokens':4,'cost':.00001})
    async def check():
        session=await authorized_session(client=FakeClient(response=response));p=OpenRouterProvider(PRIMARY_MODEL,session=session)
        with pytest.raises(ProviderFailure,match='provider_empty_response'):await complete(p)
        assert p.audit[0]['usageCostStatus']=='VERIFIED_OPENROUTER_USAGE_COST'
        assert p.audit[0]['requestId']=='local-empty' and 'rawParsedOutput' not in p.audit[0]
    asyncio.run(check())


def test_reported_cost_above_reservation_blocks_further_dispatch():
    response=types.SimpleNamespace(id='local-cost',model=PRIMARY_MODEL,provider='local-test-provider',
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"ok":true}'))],usage={'cost':.9})
    async def check():
        session=await authorized_session(client=FakeClient(response=response));p=OpenRouterProvider(PRIMARY_MODEL,session=session)
        with pytest.raises(ProviderFailure,match='openrouter_cost_exceeded_reservation'):await complete(p)
        with pytest.raises(ProviderFailure,match='openrouter_paid_dispatch_not_authorized'):await complete(p)
        assert len(session.client.create_calls)==1
    asyncio.run(check())


def test_pipeline_openrouter_prepare_does_not_dispatch_without_scope_confirmation(monkeypatch):
    from day4_fixtures import reviewed_run,boardroom_request
    from agent_day4.pipeline import run_boardroom
    from agent_day4.wire import PipelineError
    for name in ('CAUSORA_OPENROUTER_PAID_AUTHORIZED','OPENROUTER_SCOPED_KEY_CONFIRMED','CAUSORA_OPENROUTER_BUDGET_JOURNAL'):
        monkeypatch.delenv(name,raising=False)
    session=session_with_fake();primary=OpenRouterProvider(PRIMARY_MODEL,session=session);critic=OpenRouterProvider(CRITIC_MODEL,session=session)
    run=reviewed_run()
    with pytest.raises(PipelineError,match='validated') as e:asyncio.run(run_boardroom(boardroom_request(run),run=run,provider=primary,critic_provider=critic,fallback_provider=primary,correlation_id='local-preflight',config=session.config))
    assert e.value.reason=='openrouter_paid_dispatch_not_authorized' and session.client.create_calls==[]


def test_pipeline_prepare_is_async_bounded_and_uses_shared_journal(monkeypatch,tmp_path):
    import copy
    from day4_fixtures import FixtureProvider,reviewed_run,boardroom_request
    from agent_day4.pipeline import run_boardroom
    fixture=FixtureProvider()
    class DynamicCompletions:
        async def create(self,**parameters):
            stage='Critic' if parameters['model']==CRITIC_MODEL else parameters['response_format']['json_schema']['name'].removeprefix('causora_').capitalize()
            if stage in ('Cfo','Coo'):stage=stage.upper()
            if stage=='Risk':stage='Risk'
            if stage=='Synthesizer':stage='Synthesizer'
            output=await fixture.complete(stage=stage,payload=json.loads(parameters['messages'][1]['content']),schema={},system='local')
            return types.SimpleNamespace(id='local-'+stage,model=parameters['model'],provider='TEST_FIXTURE_ONLY',usage=None,
                choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=json.dumps(output)))])
    session=session_with_fake();session.client.chat.completions=DynamicCompletions()
    primary=OpenRouterProvider(PRIMARY_MODEL,session=session);critic=OpenRouterProvider(CRITIC_MODEL,session=session)
    monkeypatch.setenv('CAUSORA_OPENROUTER_PAID_AUTHORIZED','YES');monkeypatch.setenv('OPENROUTER_SCOPED_KEY_CONFIRMED','YES')
    journal=tmp_path/'shared-budget.json';monkeypatch.setenv('CAUSORA_OPENROUTER_BUDGET_JOURNAL',str(journal))
    run=reviewed_run();before=copy.deepcopy(run.simulation_response)
    result=asyncio.run(run_boardroom(boardroom_request(run),run=run,provider=primary,critic_provider=critic,fallback_provider=primary,correlation_id='local-prepared',config=session.config))
    assert result.envelope['data']['numericGuardrail']['passed']
    assert session.budget.used==5 and len(json.loads(journal.read_text())['entries'])==5
    assert run.simulation_response==before and result.audit['openrouterReadOnlyPreflight']['key']['limitRemainingUsd']=='1'
