"""Reproduce actual rejected schema/prose using local tests, not new API calls."""
import json
import pytest
from jsonschema import Draft202012Validator,ValidationError
from agent_day4.wire import provider_schema,RoleDraft,CriticDraft,SynthesisDraft,PipelineError
from day4_fixtures import FixtureProvider
from test_day4_business import terminating_run
from test_day4_pipeline import execute


@pytest.mark.parametrize('model',[RoleDraft,CriticDraft,SynthesisDraft])
def test_provider_schemas_inline_nested_references_without_relaxing_requirements(model):
    schema=provider_schema(model);Draft202012Validator.check_schema(schema)
    serialized=json.dumps(schema)
    assert '$ref' not in serialized and '$defs' not in serialized
    def check(value):
        if isinstance(value,dict):
            if value.get('type')=='object':
                assert value['additionalProperties'] is False
                assert set(value['required'])==set(value['properties'])
            for child in value.values():check(child)
        elif isinstance(value,list):
            for child in value:check(child)
    check(schema)


def test_description_only_gemini_issue_is_rejected_by_inlined_schema():
    bad={'cash_ceiling_enforced':True,'issues':[{'description':'Compound concern'}],
        'checked_roles':['CFO','COO','Risk'],'coverage':['renewal_condition','locked_forecast','minimum_commitment','demand_change','cash_pressure','holding_cost','omission','conflict']}
    with pytest.raises(ValidationError):Draft202012Validator(provider_schema(CriticDraft)).validate(bad)


@pytest.mark.parametrize('phrase',['one time cash impact','one-time cash impact','one option avoids exit'])
def test_rejected_numeric_words_remain_rejected(phrase):
    run=terminating_run();p=FixtureProvider(mutations={'Synthesizer':lambda d:{**d,'recommendation':'Terminate supplier A with '+phrase+'.'}})
    with pytest.raises(PipelineError) as error:execute(run,primary=p)
    assert error.value.reason=='numeric_guardrail_rejected'


def test_new_synthesis_task_uses_fixed_fee_and_forbids_actual_rejected_wording():
    p=FixtureProvider();execute(terminating_run(),primary=p)
    payload=next(value for stage,value in p.events if stage=='Synthesizer')
    assert 'fixed contract exit fee' in payload['task'] and 'Never say one time' in payload['task']
