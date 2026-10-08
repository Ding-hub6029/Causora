"""Focused timeout contract tests; all OpenAI clients here are local fakes."""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]
AGENT_ROOT = PROJECT_ROOT / "agents" / "wanghao-day3"
if str(AGENT_ROOT) not in sys.path:
    sys.path.insert(0, str(AGENT_ROOT))

from agent_day4.provider import ProviderFailure, providers_from_env


ENV_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_API_BASE",
    "OPENAI_BASE_URL",
    "CAUSORA_PRIMARY_MODEL",
    "CAUSORA_GEMINI_CRITIC_MODEL",
    "CAUSORA_FALLBACK_CRITIC_MODEL",
    "CAUSORA_AI_MAX_CALLS",
    "CAUSORA_AI_TOTAL_TIMEOUT",
    "CAUSORA_AI_STAGE_TIMEOUT",
    "CAUSORA_CRITIC_TIMEOUT",
    "CAUSORA_AI_RETRIES",
    "CAUSORA_AI_PIPELINE_CALLS",
)


class _FakeCompletions:
    def __init__(self, owner):
        self.owner = owner

    async def create(self, **parameters):
        self.owner.create_calls.append(parameters)
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{"ok": true}'))],
            usage=None,
        )


class FakeAsyncOpenAI:
    instances: list["FakeAsyncOpenAI"] = []
    attempts = 0
    fail_on_attempt: int | None = None

    def __init__(self, **kwargs):
        type(self).attempts += 1
        if type(self).fail_on_attempt == type(self).attempts:
            raise RuntimeError("fake SDK construction failed")
        self.kwargs = kwargs
        self.with_options_calls: list[dict] = []
        self.create_calls: list[dict] = []
        self.closed = False
        self.chat = types.SimpleNamespace(completions=_FakeCompletions(self))
        type(self).instances.append(self)

    def with_options(self, **kwargs):
        self.with_options_calls.append(kwargs)
        return self

    async def close(self):
        self.closed = True


@pytest.fixture
def factory_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_API_BASE", "https://fake.invalid/v1")
    monkeypatch.setenv("CAUSORA_PRIMARY_MODEL", "gpt-5-mini")
    monkeypatch.setenv("CAUSORA_GEMINI_CRITIC_MODEL", "gemini-3.1-pro-preview")
    monkeypatch.setenv("CAUSORA_FALLBACK_CRITIC_MODEL", "gpt-5-fallback")


def install_fake_openai(monkeypatch):
    FakeAsyncOpenAI.instances = []
    FakeAsyncOpenAI.attempts = 0
    FakeAsyncOpenAI.fail_on_attempt = None
    module = types.ModuleType("openai")
    module.AsyncOpenAI = FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", module)
    return FakeAsyncOpenAI


def complete(provider, *, stage, request_timeout=None):
    return asyncio.run(
        provider.complete(
            stage=stage,
            payload={"request": "fake only"},
            schema={"type": "object", "properties": {}, "required": []},
            system="test system",
            request_timeout=request_timeout,
        )
    )


def test_factory_uses_pipeline_defaults_and_shared_budget(factory_env, monkeypatch):
    fake = install_fake_openai(monkeypatch)
    monkeypatch.delenv("CAUSORA_FALLBACK_CRITIC_MODEL")

    primary, critic, fallback, config = providers_from_env()

    assert (config.total_timeout, config.stage_timeout, config.critic_timeout) == (40.0, 10.0, 15.0)
    assert [client.kwargs["timeout"] for client in fake.instances] == [10.0, 15.0, 15.0]
    assert all(client.kwargs["max_retries"] == 0 for client in fake.instances)
    assert primary.config is config and critic.config is config and fallback.config is config
    assert fallback.model == primary.model and fallback is not primary
    assert primary.budget is critic.budget is fallback.budget
    assert primary.budget.limit == 12
    assert primary.supports_request_timeout is True


def test_none_request_timeout_selects_role_or_critic_default_for_both_critics(factory_env, monkeypatch):
    install_fake_openai(monkeypatch)
    primary, critic, fallback, _ = providers_from_env()

    complete(primary, stage="CFO")
    complete(primary, stage="Synthesizer")
    complete(critic, stage="Critic")
    complete(fallback, stage="Critic")

    assert primary.client.with_options_calls == [{"timeout": 10.0}, {"timeout": 10.0}]
    assert critic.client.with_options_calls == [{"timeout": 15.0}]
    assert fallback.client.with_options_calls == [{"timeout": 15.0}]


def test_factory_overrides_propagate_and_request_budget_is_exact(factory_env, monkeypatch):
    fake = install_fake_openai(monkeypatch)
    monkeypatch.setenv("CAUSORA_AI_TOTAL_TIMEOUT", "39.5")
    monkeypatch.setenv("CAUSORA_AI_STAGE_TIMEOUT", "7.25")
    monkeypatch.setenv("CAUSORA_CRITIC_TIMEOUT", "13.75")
    monkeypatch.setenv("CAUSORA_AI_RETRIES", "0")
    monkeypatch.setenv("CAUSORA_AI_PIPELINE_CALLS", "9")
    monkeypatch.setenv("CAUSORA_AI_MAX_CALLS", "12")

    primary, critic, fallback, config = providers_from_env()
    assert (config.total_timeout, config.stage_timeout, config.critic_timeout, config.retries, config.max_calls) == (39.5, 7.25, 13.75, 0, 9)
    assert [client.kwargs["timeout"] for client in fake.instances] == [7.25, 13.75, 13.75]

    complete(fallback, stage="Critic", request_timeout=1.234567)
    assert fallback.client.with_options_calls == [{"timeout": 1.234567}]
    assert fallback.audit[-1]["sdkTimeoutSeconds"] == 1.234567
    assert isinstance(fallback.audit[-1]["startedAtMonotonicSeconds"], float)
    assert "elapsedSeconds" in fallback.audit[-1]
    assert primary.budget is critic.budget is fallback.budget


@pytest.mark.parametrize(
    ("name", "value"),
    (("CAUSORA_AI_STAGE_TIMEOUT", "not-a-number"), ("CAUSORA_AI_MAX_CALLS", "13")),
)
def test_invalid_environment_is_rejected_before_any_model_client(factory_env, monkeypatch, name, value):
    fake = install_fake_openai(monkeypatch)
    monkeypatch.setenv(name, value)

    with pytest.raises(ValueError):
        providers_from_env()

    assert fake.attempts == 0
    assert fake.instances == []


def test_factory_failure_closes_already_constructed_clients(factory_env, monkeypatch):
    fake = install_fake_openai(monkeypatch)
    fake.fail_on_attempt = 2

    async def construct_inside_running_loop():
        with pytest.raises(RuntimeError, match="fake SDK construction failed"):
            providers_from_env()

    asyncio.run(construct_inside_running_loop())

    assert len(fake.instances) == 1
    assert fake.instances[0].closed is True


def test_invalid_fallback_model_is_rejected_without_constructing_a_client(factory_env, monkeypatch):
    fake = install_fake_openai(monkeypatch)
    monkeypatch.setenv("CAUSORA_FALLBACK_CRITIC_MODEL", "unrecognized-model")

    with pytest.raises(ProviderFailure, match="provider_model_not_configured"):
        providers_from_env()

    assert fake.instances == []
