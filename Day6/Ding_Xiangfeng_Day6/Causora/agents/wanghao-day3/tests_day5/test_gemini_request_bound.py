"""Actual Gemini system schema is counted once, with conservative token framing."""
from types import SimpleNamespace
from agent_day4.openrouter_provider import OpenRouterProvider, OpenRouterBudget, CRITIC_MODEL, PRIMARY_MODEL, INPUT_FRAMING_TOKENS
from agent_day4.wire import PipelineConfig, CriticDraft, provider_schema

def test_schema_in_actual_gemini_system_is_not_counted_twice():
    session=SimpleNamespace(config=PipelineConfig(),budget=OpenRouterBudget())
    schema=provider_schema(CriticDraft)
    provider=OpenRouterProvider(CRITIC_MODEL,session=session)
    params,size,bound,_=provider._parameters(stage='Critic',body='{}',schema=schema,system='Review.')
    actual=sum(len(message['content'].encode()) for message in params['messages'])
    assert size==actual
    assert bound==actual+INPUT_FRAMING_TOKENS
    assert 'schema' not in params['response_format']
    assert 'cash_ceiling_enforced' in params['messages'][0]['content']
