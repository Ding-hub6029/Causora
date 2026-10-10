"""Current-allocation regressions; every provider below is TEST_FIXTURE_ONLY."""
import copy
import pytest
from agent_day4.allocation import allocation_facts,result_facts,check_prose,check_required_exit_explanation,terminating_brief
from agent_day4.wire import PipelineError,SynthesisDraft
from day4_fixtures import FixtureProvider
from test_day4_business import terminating_run
from test_day4_pipeline import execute

BAD_CONCENTRATION=[
    'Moving entirely to supplier B reduces overall supplier concentration.',
    'Termination lowers supplier concentration.',
    'The sourcing plan achieves supplier diversification.',
    'The result provides a diversified supplier base.',
    'The plan improves diversification.',
    'The sourcing action reduces concentration.',
    'The plan eliminates single-supplier dependence.',
    'Reduced dependence on A lowers overall concentration.',
]

@pytest.mark.parametrize('text',BAD_CONCENTRATION)
def test_b_only_unsupported_benefit_rejected_from_actual_shares(text):
    run=terminating_run();facts=result_facts(run,'demand-drop')
    with pytest.raises(PipelineError) as e:check_prose(text,facts=facts,default_option_id='D2',stage='regression')
    assert 'unsupported_' in ' '.join(e.value.details['violations'])

@pytest.mark.parametrize('text',[
    'The allocation lowers dependence on A but supply remains concentrated in B.',
    'This is not supplier diversification and does not reduce overall supplier concentration.',
    'Reduced dependence on A is not reduced overall supplier concentration.',
    'B-only sourcing retains concentrated supply and delivery risk.',
    'Monitor B delivery risk and the computed shortage likelihood.',
    'Consider future supplier diversification beyond the selected B-only sourcing plan.',
    'Account for the fixed exit fee within the existing cash ceiling.',
])
def test_correct_risk_warning_and_explicit_negation_are_allowed(text):
    check_prose(text,facts=result_facts(terminating_run(),'demand-drop'),default_option_id='D2',stage='positive')

@pytest.mark.parametrize('stage',['CFO','COO','Risk','Synthesizer'])
def test_bad_current_stage_cannot_publish_brief(stage):
    run=terminating_run();before=copy.deepcopy(run.simulation_response)
    def bad(value):
        field='rationale' if stage=='Synthesizer' else 'body'
        return {**value,field:'The sourcing action reduces overall supplier concentration.'}
    with pytest.raises(PipelineError) as e:execute(run,primary=FixtureProvider(mutations={stage:bad}))
    assert e.value.reason in ('roles_incomplete','business_semantic_contradiction')
    if stage!='Synthesizer':assert e.value.details['failureReasons'][stage]=='business_semantic_contradiction'
    assert before==run.simulation_response


def bad_issue(value):
    value['issues'][0]['body']='The B-only plan realizes supplier diversification.'
    return value


def test_invalid_gemini_local_fixture_falls_back_without_publishing_bad_issue():
    result=execute(terminating_run(),critic=FixtureProvider(mutations={'Critic':bad_issue}))
    assert result.audit['fallbackReason']=='business_semantic_contradiction'
    assert result.headers['X-Causora-Provider-Mode']=='same-family-fallback'
    assert not any('realizes supplier diversification' in i['body'] for i in result.envelope['data']['criticIssues'])


def test_both_critics_bad_concentration_produce_no_brief():
    run=terminating_run();before=copy.deepcopy(run.simulation_response)
    with pytest.raises(PipelineError) as e:execute(run,critic=FixtureProvider(mutations={'Critic':bad_issue}),fallback=FixtureProvider(mutations={'Critic':bad_issue}))
    assert e.value.reason=='critic_unavailable'
    assert run.simulation_response==before

@pytest.mark.parametrize('text,violation',[
    ('The selected plan incurs no exit fee.','applicable_exit_fee_denied'),
    ('The termination fee is waived.','applicable_exit_fee_denied'),
    ('This is a fee-free exit.','applicable_exit_fee_denied'),
    ('The selected plan eliminates stockout risk.','computed_stockout_risk_denied'),
    ('The result guarantees uninterrupted supply.','computed_stockout_risk_denied'),
    ('The selected plan breaches the cash ceiling.','computed_cash_compliance_denied'),
    ('The result retains both suppliers.','b_only_described_as_mixed_allocation'),
])
def test_fee_risk_cash_and_allocation_assertions_match_mc(text,violation):
    with pytest.raises(PipelineError) as e:check_prose(text,facts=result_facts(terminating_run(),'demand-drop'),default_option_id='D2',stage='risk')
    assert violation in e.value.details['violations']


def test_mixed_allocation_may_reduce_concentration_when_source_supports_it():
    run=terminating_run();facts=result_facts(run,'demand-drop')
    assert facts['D1']['mixedSuppliers'] and facts['D1']['overallConcentrationLowerThanBaseline']
    check_prose('The mixed-allocation alternative reduces overall supplier concentration.',facts=facts,default_option_id='D2',stage='alternative')
    check_prose('The allocation reduces supplier concentration.',facts=facts,default_option_id='D1',stage='mixed')


def test_concentration_is_same_at_full_a_and_full_b_not_new_simulated_metric():
    run=terminating_run();before=copy.deepcopy(run.simulation_response);facts=allocation_facts(run.simulation_request['options'])
    assert facts['D0']['concentrationIndex']==facts['D2']['concentrationIndex']==1
    assert not facts['D2']['overallConcentrationLowerThanBaseline']
    assert facts['D2']['dependenceOnALowerThanBaseline'] and facts['D2']['singleSupplierDependence']
    assert before==run.simulation_response


def test_d2_source_contradictory_share_or_fee_is_not_accepted():
    run=terminating_run();run.simulation_request['options'][2]['shareA']=.1
    with pytest.raises(PipelineError,match='validated'):allocation_facts(run.simulation_request['options'])
    run=terminating_run();next(row for row in run.simulation_response['data']['simulation']['matrix']['demand-drop'] if row['optionId']=='D2')['breakdown']['terminationFee']=0
    with pytest.raises(PipelineError):result_facts(run,'demand-drop')


def test_current_generation_payload_preserves_role_metric_isolation():
    run=terminating_run();provider=FixtureProvider();execute(run,primary=provider)
    role_inputs={stage:payload for stage,payload in provider.events if stage in ('CFO','COO','Risk')}
    for role,payload in role_inputs.items():
        allocation=payload['allocationFactsByOptionId']['D2']
        assert allocation['shareA']==0 and allocation['allSupplyFromB']
        assert 'terminationFeeUsd' not in allocation and 'stockoutProbability' not in allocation and 'cashOutflowP90Usd' not in allocation
        assert 'NOT overall supplier concentration' in payload['allocationInterpretation']
        assert ('finance' in payload)==(role=='CFO') and ('operations' in payload)==(role=='COO') and ('risk' in payload)==(role=='Risk')


def test_current_brief_requires_actual_exit_tradeoffs():
    run=terminating_run();result=execute(run);brief=result.envelope['data']['brief']
    assert 'Terminate supplier A and move procurement to supplier B' in brief['recommendation']
    assert 'concentrated in B' in brief['rationale'] and 'exit fee' in brief['rationale'] and 'delivery risk' in brief['rationale']
    assert result.audit['businessConsistency']['allocation']['overallConcentrationLowerThanBaseline'] is False
    draft=SynthesisDraft.model_validate({'option_id':'D2','option_action':'terminate_supplier_a','cash_ceiling_enforced':True,
        'recommendation':'Terminate supplier A.','rationale':'Use the alternative.','metric_refs':['delta_tco'],'claims':[],'challenges':[]})
    with pytest.raises(PipelineError) as e:check_required_exit_explanation(draft,fact=result_facts(run,'demand-drop')['D2'])
    assert 'b_supply_concentration_not_explained' in e.value.details['violations']


def test_code_fallback_brief_is_guarded_and_correct():
    facts=result_facts(terminating_run(),'demand-drop');recommendation,rationale=terminating_brief(facts['D2'])
    assert 'supplier B' in recommendation
    check_prose(recommendation+' '+rationale,facts=facts,default_option_id='D2',stage='code-fallback')


def test_synthesis_challenge_is_not_an_unguarded_escape_hatch():
    p=FixtureProvider(mutations={'Synthesizer':lambda d:{**d,'challenges':['The B-only sourcing plan achieves supplier diversification.']}})
    with pytest.raises(PipelineError):execute(terminating_run(),primary=p)

@pytest.mark.parametrize('text,violation',[
    ('The selected plan retains supplier A.','terminated_supplier_a_retained'),
    ('The selected plan avoids termination.','termination_described_as_avoiding_exit'),
    ('The selected plan achieves a balanced supplier mix.','b_only_described_as_mixed_allocation'),
])
def test_action_prose_is_checked_in_every_model_stage(text,violation):
    facts=result_facts(terminating_run(),'demand-drop')
    for stage in ('CFO','COO','Risk','Critic','Synthesizer','Brief'):
        with pytest.raises(PipelineError) as e:check_prose(text,facts=facts,default_option_id='D2',stage=stage)
        assert violation in e.value.details['violations']


def test_new_model_generation_context_is_present_at_critic_and_synthesizer():
    primary=FixtureProvider();critic=FixtureProvider();critic.family='google-gemini';execute(terminating_run(),primary=primary,critic=critic)
    for stage,payload in critic.events+primary.events:
        if stage not in ('Critic','Synthesizer'):continue
        assert 'NOT overall supplier concentration' in payload['allocationInterpretation']
        facts=payload['verifiedBusinessFacts']['allocationFactsByOptionId']['D2']
        assert facts['allSupplyFromB'] and not facts['overallConcentrationLowerThanBaseline']
        assert facts['terminationFeeUsd']>0 and facts['stockoutProbability']>0
        assert facts['cashWithinCeiling'] is True


def test_raw_old_result_is_retained_but_new_guard_does_not_accept_its_bad_concentration():
    import json
    from day4_fixtures import ROOT
    audit_path=ROOT/'provenance/historical-verification/wang_day4/followup/live_second/fresh_full_pipeline.json'
    original=audit_path.read_bytes();raw=json.loads(original)
    rationale=raw['draft']['brief']['rationale']
    assert 'reduces concentration' in rationale
    with pytest.raises(PipelineError):check_prose(rationale,facts=result_facts(terminating_run(),'demand-drop'),default_option_id='D2',stage='OLD_VERSION_ONLY')
    assert audit_path.read_bytes()==original

