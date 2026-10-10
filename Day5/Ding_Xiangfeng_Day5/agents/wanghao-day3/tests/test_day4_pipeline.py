"""Day4 pipeline fixture tests; none is a real-provider score or team approval."""
import asyncio,copy,json,time
import pytest
from day4_fixtures import FixtureProvider,reviewed_run,boardroom_request
from agent_day4.pipeline import run_boardroom
from agent_day4.wire import PipelineConfig,PipelineError
from agent_day4.provider import ProviderFailure


def execute(run=None,*,primary=None,critic=None,fallback=None,scenario='demand-drop',config=None,request=None):
    run=run or reviewed_run();primary=primary or FixtureProvider();critic=critic or FixtureProvider()
    critic.family='google-gemini';critic.model='TEST_FIXTURE_ONLY-gemini'
    return asyncio.run(run_boardroom(request or boardroom_request(run,scenario),run=run,provider=primary,critic_provider=critic,
       fallback_provider=fallback or primary,correlation_id='br-TEST_FIXTURE_ONLY',config=config or PipelineConfig(stage_timeout=1,critic_timeout=1,total_timeout=5)))


def recompute_selections(run):
    request=run.simulation_request;data=run.simulation_response['data']
    for sid,rows in data['simulation']['matrix'].items():
        violations=[];eligible=[]
        for row in rows:
            codes=[]
            if not row['feasible']:codes.append('infeasible')
            if row['stockoutProbability']>request['riskThreshold']:codes.append('stockout_threshold')
            if row['cashOutflowP90']>request['budgetCeilingUsd']:codes.append('cash_ceiling')
            violations.extend({'optionId':row['optionId'],'code':code} for code in codes)
            if not codes:eligible.append(row)
        winner=min(eligible,key=lambda r:(r['expectedTco'],r['optionId']))['optionId'] if eligible else None
        data['selections'][sid]={'scenarioId':sid,'status':'selected' if winner else 'no_feasible_option','recommendedOptionId':winner,'constraintViolations':violations}


@pytest.mark.parametrize('scenario',['baseline','demand-drop','lead-stress'])
def test_three_roles_real_code_concurrent_and_front_order(scenario):
    p=FixtureProvider(delay=.04);result=execute(primary=p,scenario=scenario)
    assert p.max_active==3
    assert [o['role'] for o in result.envelope['data']['agentOutputs']]==['CFO','COO','Risk']
    stages=[s for s,_ in p.events];assert stages[:3]==['CFO','COO','Risk'];assert stages[-1]=='Synthesizer'
    role_events=[e for e in result.audit['events'] if e['stage'] in ('CFO','COO','Risk')]
    assert max(e['startedOffsetSeconds'] for e in role_events)-min(e['startedOffsetSeconds'] for e in role_events)<.2
    assert result.headers['X-Request-Id']==result.envelope['requestId']=='br-TEST_FIXTURE_ONLY'
    assert result.envelope['data']['numericGuardrail']=={'passed':True,'rejectedClaims':[]}


def test_allowlists_are_not_prompts_over_complete_snapshot():
    p=FixtureProvider();execute(primary=p)
    payloads=dict(p.events[:3]);cfo=json.dumps(payloads['CFO']);coo=json.dumps(payloads['COO']);risk=json.dumps(payloads['Risk'])
    assert 'stockoutProbability' not in cfo and 'serviceLevel' not in cfo and 'traces' not in cfo
    assert 'expectedTco' not in coo and 'cashOutflowP90' not in coo and 'terminationFee' not in coo
    assert 'sourceFile' not in risk and 'sourceSha256' not in risk and 'samplePath' not in risk


def test_critic_mechanism_is_code_bound_current_scenario():
    run=reviewed_run();result=execute(run);issue=result.envelope['data']['criticIssues'][0]
    scenario=next(s for s in run.simulation_request['scenarios'] if s['id']=='demand-drop');m=issue['mechanism']
    assert m['scenarioId']=='demand-drop' and m['scenarioDemandUnits24m']==scenario['demandUnits24m']
    assert m['committedExcessUnits']==max(0,run.contract['minPurchaseUnitsA']-round(run.contract['minPurchaseShareA']*scenario['demandUnits24m']))
    rows=run.simulation_response['data']['simulation']['matrix']['demand-drop'];base=next(r for r in rows if r['optionId']=='D0')
    assert m['holdingCostDeltaUsd']=={r['optionId']:r['breakdown']['holding']-base['breakdown']['holding'] for r in rows}
    assert set(m)=={'scenarioId','forecastBasis','lockedForecastUnits24m','minPurchaseUnitsA','scenarioDemandUnits24m','committedExcessUnits','holdingCostDeltaUsd'}


def test_gemini_timeout_same_family_success_and_double_failure_preserve_snapshot():
    run=reviewed_run();before=copy.deepcopy(run.simulation_response)
    critic=FixtureProvider(failures={'Critic':ProviderFailure('provider_timeout')});critic.family='google-gemini'
    result=execute(run,critic=critic);assert result.headers['X-Causora-Provider-Mode']=='same-family-fallback'
    assert result.audit['fallbackReason']=='provider_timeout'
    primary=FixtureProvider(failures={'Critic':ProviderFailure('provider_unavailable')})
    with pytest.raises(PipelineError,match='validated') as e:execute(run,primary=primary,critic=critic)
    assert e.value.reason=='critic_unavailable';assert run.simulation_response==before


def test_fallback_family_must_match_primary():
    fallback=FixtureProvider();fallback.family='other-family'
    with pytest.raises(PipelineError) as e:execute(critic=FixtureProvider(failures={'Critic':ProviderFailure('provider_unavailable')}),fallback=fallback)
    assert e.value.reason=='fallback_not_same_family'


@pytest.mark.parametrize('role',['CFO','COO','Risk'])
def test_single_role_failure_never_runs_critic_or_synthesizer(role):
    primary=FixtureProvider(failures={role:ProviderFailure('provider_unavailable')});critic=FixtureProvider()
    with pytest.raises(PipelineError) as e:execute(primary=primary,critic=critic)
    assert e.value.reason=='roles_incomplete';assert role in e.value.details['failedRoles'];assert not critic.events
    assert not any(s=='Synthesizer' for s,_ in primary.events)


def test_rate_limit_retry_is_finite_then_success():
    attempts=0
    class Limited(FixtureProvider):
        async def complete(self,**kw):
            nonlocal attempts
            if kw['stage']=='CFO':
                attempts+=1
                if attempts==1:raise ProviderFailure('provider_rate_limited')
            return await super().complete(**kw)
    result=execute(primary=Limited());assert attempts==2;assert result.audit['providerCalls']==6


def test_unavailable_and_malformed_are_not_canned_model_success():
    bad=FixtureProvider(mutations={'CFO':lambda _: {'wrong':'shape'}})
    with pytest.raises(PipelineError) as e:execute(primary=bad)
    assert e.value.reason=='roles_incomplete'
    critic=FixtureProvider(mutations={'Critic':lambda _: {'wrong':'shape'}})
    result=execute(critic=critic);assert result.headers['X-Causora-Provider-Mode']=='same-family-fallback'


def test_synthesizer_cannot_invent_fourth_option():
    p=FixtureProvider(mutations={'Synthesizer':lambda d:{**d,'option_id':'D3'}})
    with pytest.raises(PipelineError) as e:execute(primary=p)
    assert e.value.reason=='invalid_synthesizer_option'


def test_feasible_model_disagreement_only_becomes_audit_challenge():
    run=reviewed_run();run.simulation_request['riskThreshold']=1.;run.simulation_request['budgetCeilingUsd']=10**9;recompute_selections(run)
    selection=run.simulation_response['data']['selections']['demand-drop']['recommendedOptionId'];other=next(o for o in ('D0','D1','D2') if o!=selection)
    from agent_day4.business import action_for
    action=action_for(next(o for o in run.simulation_request['options'] if o['id']==other))
    recommendation='Terminate supplier A.' if action=='terminate_supplier_a' else 'Follow the proposed supplier allocation.'
    p=FixtureProvider(mutations={'Synthesizer':lambda d:{**d,'option_id':other,'option_action':action,'recommendation':recommendation}});result=execute(run,primary=p)
    assert result.envelope['data']['brief']['recommendedOptionId']==selection
    assert result.audit['synthesisChallenge']==other and 'does not override' in result.envelope['data']['brief']['rationale']


@pytest.mark.parametrize('body',['Unbound cost $999,999.', 'Declined by twenty percent.', 'Unknown {{stockout_prob}}.', 'Missing {{delta_tco}.', 'Undeclared {{stockout_probability}}.'])
def test_numeric_bad_claims_and_tokens_never_enter_summary(body):
    p=FixtureProvider(mutations={'CFO':lambda d:{**d,'body':body}})
    with pytest.raises(PipelineError) as e:execute(primary=p)
    assert e.value.reason=='numeric_guardrail_rejected'


def test_unknown_evidence_fails_in_evidence_layer_not_critic_credit():
    p=FixtureProvider(mutations={'Risk':lambda d:{**d,'evidence_ids':['EV-999']}})
    with pytest.raises(PipelineError) as e:execute(primary=p)
    assert e.value.reason=='evidence_reference_invalid'


def test_compound_omission_triggers_fallback_not_passed_coverage_only():
    p=FixtureProvider();c=FixtureProvider(mutations={'Critic':lambda d:{**d,'issues':[]}})
    result=execute(primary=p,critic=c);assert result.headers['X-Causora-Provider-Mode']=='same-family-fallback'
    assert result.audit['fallbackReason']=='critic_compound_risk_omitted'


def test_no_feasible_option_calls_no_model():
    run=reviewed_run();run.simulation_request['budgetCeilingUsd']=0;recompute_selections(run);p=FixtureProvider();c=FixtureProvider()
    result=execute(run,primary=p,critic=c)
    assert result.envelope['data']['brief']['status']=='no_feasible_option';assert result.envelope['data']['brief']['recommendedOptionId'] is None
    assert result.envelope['data']['agentOutputs']==[] and not p.events and not c.events


@pytest.mark.parametrize('key,value',[('simulationId','stale'),('dataVersion','stale'),('scenarioId','not-current')])
def test_stale_request_rejected_before_models(key,value):
    run=reviewed_run();request=boardroom_request(run);request[key]=value;p=FixtureProvider()
    with pytest.raises(PipelineError) as e:execute(run,primary=p,request=request)
    assert e.value.reason=='stale_boardroom_identity';assert not p.events


def test_overall_timeout_cancels_roles_and_keeps_original_simulation():
    run=reviewed_run();before=copy.deepcopy(run.simulation_response);p=FixtureProvider(delay=.5)
    with pytest.raises(PipelineError) as e:execute(run,primary=p,config=PipelineConfig(total_timeout=.05,stage_timeout=1,critic_timeout=1,retries=0))
    assert e.value.reason=='provider_timeout';assert len(p.cancellations)==len(p.events);assert p.active==0
    assert all(stage in ('CFO','COO','Risk') for stage,_ in p.events);assert run.simulation_response==before


def test_external_cancel_releases_tasks_and_keeps_snapshot():
    async def go():
        run=reviewed_run();before=copy.deepcopy(run.simulation_response);p=FixtureProvider(delay=1)
        task=asyncio.create_task(run_boardroom(boardroom_request(run),run=run,provider=p,critic_provider=p,fallback_provider=p,correlation_id='br-cancel'))
        await asyncio.sleep(.15);task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert run.simulation_response==before;assert p.active==0
    asyncio.run(go())


def test_rejected_numeric_draft_is_retried_once_without_accepting_bad_claim():
    attempts=0
    def mutate(value):
        nonlocal attempts
        attempts+=1
        return {**value,'body':'Rejected $999,999.'} if attempts==1 else value
    primary=FixtureProvider(mutations={'CFO':mutate});result=execute(primary=primary)
    assert attempts==2 and result.audit['rejectedModelDrafts'][0]['stage']=='CFO'
    assert '$999,999' not in json.dumps(result.envelope)


def test_selected_public_token_cannot_be_attached_to_other_option():
    run=reviewed_run();selection=run.simulation_response['data']['selections']['demand-drop']['recommendedOptionId']
    other=next(o for o in ('D0','D1','D2') if o!=selection)
    p=FixtureProvider(mutations={'CFO':lambda d:{**d,'body':f'Option {other} cash exposure {{{{cash_outflow_p90}}}}.'}})
    with pytest.raises(PipelineError) as e:execute(run,primary=p)
    assert e.value.reason=='numeric_guardrail_rejected'


def test_synthesis_receives_verified_option_exit_semantics_and_current_metrics():
    run=reviewed_run();p=FixtureProvider();result=execute(run,primary=p)
    payload=next(v for stage,v in p.events if stage=='Synthesizer');chosen=result.envelope['data']['brief']['recommendedOptionId']
    assert payload['selectedOption']==next(o for o in run.simulation_request['options'] if o['id']==chosen)
    assert json.loads(json.dumps(payload['currentScenarioMatrix']))==run.simulation_response['data']['simulation']['matrix']['demand-drop']
    assert {o['id']:o['terminateA'] for o in payload['options']}=={'D0':False,'D1':False,'D2':True}


@pytest.mark.parametrize('wrong_digest',[True,False])
def test_development_checkpoint_cannot_change_snapshot_or_use_fixture_as_live(wrong_digest):
    from agent_day4.cli import run_from_capture
    from agent_day4.pipeline import run_development_analysis,_run_digest
    from day4_fixtures import ROOT,BACKEND
    capture=json.loads((ROOT/'provenance/historical-verification/wang_day4/live/changed-lead_simulation.json').read_text(encoding='utf-8'))
    run=run_from_capture(capture,BACKEND);p=FixtureProvider()
    checkpoint={'kind':'EXPLICIT_ACTUAL_DEVELOPMENT_STAGE_CHECKPOINT','simulationSnapshotSha256':'wrong' if wrong_digest else _run_digest(run)}
    with pytest.raises(PipelineError) as e:
        asyncio.run(run_development_analysis(boardroom_request(run),run=run,provider=p,critic_provider=p,fallback_provider=p,
            correlation_id='br-checkpoint-TEST_ONLY',role_checkpoint=checkpoint))
    assert e.value.reason==('checkpoint_input_mismatch' if wrong_digest else 'checkpoint_provider_not_live')
    assert not p.events


def test_cli_no_feasible_does_not_construct_provider(monkeypatch,tmp_path):
    from types import SimpleNamespace
    from agent_day4 import cli
    run=reviewed_run();run.simulation_request['budgetCeilingUsd']=0;recompute_selections(run)
    monkeypatch.setattr(cli,'read_json',lambda _: {})
    monkeypatch.setattr(cli,'run_from_capture',lambda *args:run)
    def forbidden():raise AssertionError('Provider must remain unconstructed')
    monkeypatch.setattr(cli,'providers_from_env',forbidden)
    args=SimpleNamespace(capture='unused',source_root='unused',enable_unreviewed_dev=False,scenario='demand-drop',output=tmp_path/'no-feasible.json')
    asyncio.run(cli.analyse_capture(args))
    result=json.loads(args.output.read_text(encoding='utf-8'))
    assert result['envelope']['data']['brief']['recommendedOptionId'] is None
    assert result['audit']['providerCalls']==0

