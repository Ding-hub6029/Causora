"""Regressions from the actual integrated baseline audit; no provider calls."""
import asyncio
import pytest
from day4_fixtures import reviewed_run as fixture_run
from agent_day4.allocation import result_facts,check_prose
from agent_day4.pipeline import _Execution,_check_refs
from agent_day4.wire import PipelineConfig,PipelineError,RoleDraft,ROLE_TOKENS

@pytest.mark.parametrize('text',[
    'Delivery risk is aligned with B-only sourcing characteristics.',
    'Selected rebalance lowers reliance on A while concentrating supply with supplier B.',
    'The plan uses exclusive sourcing from supplier B.',
    'Supply remains concentrated in supplier B.',
])
def test_mixed_selection_rejects_sole_b_assertions(text):
    with pytest.raises(PipelineError) as caught:
        check_prose(text,facts=result_facts(fixture_run(),'baseline'),default_option_id='D1',stage='Risk')
    assert 'mixed_allocation_described_as_b_only' in caught.value.details['violations']

@pytest.mark.parametrize('text',[
    'The chosen plan is not B-only sourcing.',
    'The all-B alternative would concentrate supply with supplier B.',
    'Consider the all B exit as a conditional alternative that would reduce dependence on supplier A but concentrate supply in supplier B.',
    'An exit to supplier B is a separate conditional alternative with fixed exit cost and B-only sourcing risks; that exit is not the selected mix.',
    'Supply remains concentrated in supplier B for any conditional all B exit.',
    'Supply is concentrated in supplier B for the portion moved, while the selected mix retains A.',
    'Mixed sourcing retains A participation and reduces concentration.',
])
def test_mixed_selection_allows_negation_and_labelled_exit_alternative(text):
    check_prose(text,facts=result_facts(fixture_run(),'baseline'),default_option_id='D1',stage='Risk')

def test_captured_braced_coo_reference_remains_rejected_locally():
    with pytest.raises(PipelineError) as caught:
        _check_refs(['{{stockout_probability}}'],ROLE_TOKENS['COO'],'metric')
    assert caught.value.reason=='metric_reference_invalid'

def test_provider_schema_binds_role_and_bare_metric_identifiers():
    class Provider:
        async def complete(self,**kwargs):
            props=kwargs['schema']['properties']
            assert props['role']['enum']==['COO']
            assert props['metric_refs']['items']['enum']==['stockout_probability']
            return {'role':'COO','headline':'Inspect delivery risk','body':'Review current service metrics.',
                'status':'Watch','metric_refs':['stockout_probability'],'evidence_ids':[],
                'option_ids':['D0','D1','D2'],'claims':[]}
    asyncio.run(_Execution(PipelineConfig(retries=0)).call(Provider(),'COO',{},RoleDraft))
