"""Returned contradictory prose can be regenerated, never accepted unchecked."""
import pytest
from agent_day4.wire import PipelineConfig, PipelineError
from tests_day5.day5_fixtures import FixtureProvider, execute

class ContradictoryRole(FixtureProvider):
    def __init__(self, always_invalid=False):
        super().__init__()
        self.operations=0
        self.always_invalid=always_invalid

    async def complete(self, **kwargs):
        output=await super().complete(**kwargs)
        if kwargs['stage']=='COO':
            self.operations+=1
            if self.operations==1 or self.always_invalid:
                output['body']='All supply is from supplier B.'
        return output

def config(calls=6):
    return PipelineConfig(total_timeout=4,stage_timeout=.5,critic_timeout=.5,retries=0,max_calls=calls)

def test_corrected_role_passes_original_checks_and_whole_run_cap():
    provider=ContradictoryRole()
    result=execute(primary=provider,config=config())
    assert provider.operations==2
    assert result.audit['providerCalls']==6
    assert result.audit['rejectedModelDrafts'][0]['reason']=='business_semantic_contradiction'
    assert result.envelope['data']['numericGuardrail']['passed'] is True
    assert 'All supply' not in str(result.envelope['data']['agentOutputs'])

def test_invalid_correction_still_fails_closed():
    provider=ContradictoryRole(always_invalid=True)
    with pytest.raises(PipelineError) as error:
        execute(primary=provider,config=config())
    assert error.value.reason=='business_semantic_contradiction'
    assert provider.operations==2
    assert not any(stage=='Critic' for stage,_ in provider.events)

def test_no_spare_call_does_not_dispatch_correction():
    provider=ContradictoryRole()
    with pytest.raises(PipelineError):
        execute(primary=provider,config=config(5))
    assert provider.operations==1
