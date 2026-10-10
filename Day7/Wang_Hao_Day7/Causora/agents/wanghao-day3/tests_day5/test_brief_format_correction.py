"""Offline checks: one bounded repair never bypasses the numeric guardrail."""
import pytest
from agent_day4.wire import PipelineConfig, PipelineError
from tests_day5.day5_fixtures import FixtureProvider, execute

class NumericBriefProvider(FixtureProvider):
    def __init__(self, always_invalid=False):
        super().__init__()
        self.briefs=0
        self.always_invalid=always_invalid

    async def complete(self, **kwargs):
        output=await super().complete(**kwargs)
        if kwargs['stage']=='Synthesizer':
            self.briefs+=1
            if self.always_invalid or self.briefs==1:
                output['rationale']='The expected cost is $999.'
        return output

def config(calls=6):
    return PipelineConfig(total_timeout=4,stage_timeout=.5,critic_timeout=.5,retries=0,max_calls=calls)

def test_one_corrective_generation_returns_only_revalidated_brief():
    provider=NumericBriefProvider()
    result=execute(primary=provider,config=config())
    assert provider.briefs==2
    assert result.audit['providerCalls']==6
    assert result.envelope['data']['numericGuardrail']['passed'] is True
    assert '$999' not in result.envelope['data']['brief']['rationale']
    assert provider.events[-1][1]['rejectedDraft']['rationale'].endswith('$999.')

def test_invalid_correction_remains_rejected_without_third_attempt():
    provider=NumericBriefProvider(always_invalid=True)
    with pytest.raises(PipelineError) as error:
        execute(primary=provider,config=config())
    assert error.value.reason=='numeric_guardrail_rejected'
    assert provider.briefs==2

def test_exhausted_call_cap_never_dispatches_correction():
    provider=NumericBriefProvider()
    with pytest.raises(PipelineError):
        execute(primary=provider,config=config(5))
    assert provider.briefs==1
