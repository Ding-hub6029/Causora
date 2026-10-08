"""Targeted semantic regressions; local fixture providers, no live API calls."""
import copy
import pytest
from pydantic import ValidationError
from agent_day4.business import check_cash_prose,check_synthesis,facts_for
from agent_day4.wire import SynthesisDraft,PipelineError,CriticDraft
from day4_fixtures import FixtureProvider,reviewed_run
from test_day4_pipeline import execute,recompute_selections


def terminating_run():
    run=reviewed_run();run.simulation_request['riskThreshold']=1.;run.simulation_request['budgetCeilingUsd']=10**9
    recompute_selections(run)
    assert run.simulation_response['data']['selections']['demand-drop']['recommendedOptionId']=='D2'
    return run


def draft(**changes):
    return SynthesisDraft.model_validate({'option_id':'D2','option_action':'terminate_supplier_a','cash_ceiling_enforced':True,
        'recommendation':'Terminate supplier A and move procurement to supplier B.',
        'rationale':'The current cash ceiling is enforced and the exit fee is included in this choice.',
        'metric_refs':['cash_outflow_p90'],'claims':[],'challenges':[],**changes})


@pytest.mark.parametrize('text',[
    'This avoids exit actions while gradually adjusting suppliers.',
    'Terminate supplier A while minimizing the need for abrupt exit actions.',
    'Terminate supplier A through phased supplier mix adjustments.',
    'Terminate supplier A by adjusting supplier shares gradually.',
    'Retain supplier A while describing contract termination.',
    'Do not terminate supplier A.',
    'The alternative follows the preferred cost profile.',
])
def test_termination_prose_contradiction_cannot_be_published(text):
    run=terminating_run();before=copy.deepcopy(run.simulation_response)
    p=FixtureProvider(mutations={'Synthesizer':lambda d:{**d,'recommendation':text,'rationale':'Respect the existing cash ceiling.'}})
    with pytest.raises(PipelineError) as exc:execute(run,primary=p)
    assert exc.value.reason=='business_semantic_contradiction'
    assert run.simulation_response==before


def test_structured_action_cannot_override_true_termination():
    run=terminating_run()
    with pytest.raises(PipelineError) as exc:check_synthesis(draft(option_action='rebalance_suppliers'),run.simulation_request['options'])
    assert 'option_action_mismatch' in exc.value.details['violations']


@pytest.mark.parametrize('text',[
    'The system has no cash ceiling rule.',
    'The cash ceiling is not enforced.',
    'Finance cannot enforce upper bounds on commitments.',
    'There is no explicit rule linking projected cash exposure to the stated treasury ceiling.',
    'The simulation runs without an enforced cash limit.',
    'The cash cap is missing.',
])
def test_existing_cash_rule_denial_is_rejected_even_with_true_flag(text):
    with pytest.raises(PipelineError,match='validated') as exc:check_cash_prose(text,stage='Critic')
    assert exc.value.details['violations']==['existing_cash_ceiling_denied']
    def bad(d):
        value=copy.deepcopy(d);value['issues'][0]['body']=text;return value
    result=execute(critic=FixtureProvider(mutations={'Critic':bad}))
    assert result.headers['X-Causora-Provider-Mode']=='same-family-fallback'
    assert result.audit['fallbackReason']=='business_semantic_contradiction'
    assert all(text not in issue['body'] for issue in result.envelope['data']['criticIssues'])


@pytest.mark.parametrize('text',[
    'The simulation already enforces a cash ceiling. An additional manual escalation process could be documented.',
    'Cash exposure must remain within the enforced ceiling without exceeding the limit.',
    'No missing cash ceiling was found.',
])
def test_existing_cash_rule_and_additional_governance_are_allowed(text):
    check_cash_prose(text,stage='Critic')


def test_correct_termination_reason_and_cash_acknowledgment_pass():
    run=terminating_run();result=execute(run)
    assert 'Terminate supplier A' in result.envelope['data']['brief']['recommendation']
    assert result.audit['businessConsistency']['selectedAction']=='terminate_supplier_a'
    assert result.audit['businessConsistency']['cashCeilingEnforced'] is True
    facts=facts_for(run,'demand-drop')
    row=next(r for r in run.simulation_response['data']['simulation']['matrix']['demand-drop'] if r['optionId']=='D2')
    assert facts['terminationFeeUsd']==row['breakdown']['terminationFee']
    assert facts['cashCeilingRule']['selectedCashOutflowP90Usd']==row['cashOutflowP90']
    assert facts['cashCeilingRule']['ceilingUsd']==run.simulation_request['budgetCeilingUsd']


def test_both_critics_denying_cash_rules_fail_instead_of_publishing():
    def bad(d):
        value=copy.deepcopy(d);value['issues'][0]['body']='The system has no cash ceiling.';return value
    with pytest.raises(PipelineError) as exc:execute(critic=FixtureProvider(mutations={'Critic':bad}),fallback=FixtureProvider(mutations={'Critic':bad}))
    assert exc.value.reason=='critic_unavailable'


def test_false_cash_acknowledgment_is_not_valid_internal_schema():
    with pytest.raises(ValidationError):draft(cash_ceiling_enforced=False)
    with pytest.raises(ValidationError):CriticDraft.model_validate({'cash_ceiling_enforced':False,'issues':[],
        'checked_roles':['CFO','COO','Risk'],'coverage':['renewal_condition','locked_forecast','minimum_commitment','demand_change','cash_pressure','holding_cost','omission','conflict']})
