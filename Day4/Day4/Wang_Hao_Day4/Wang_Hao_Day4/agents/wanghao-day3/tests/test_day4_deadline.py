"""Local asynchronous timeout/fallback tests; never invoke a remote model."""
import asyncio,copy,time,json,os
from pathlib import Path
import pytest
from day4_fixtures import FixtureProvider,reviewed_run
from test_day4_pipeline import execute
from agent_day4.pipeline import _Execution
from agent_day4.wire import PipelineConfig,PipelineError,RoleDraft


class BudgetAwareFixture(FixtureProvider):
    supports_request_timeout=True
    def __init__(self,**kwargs):super().__init__(**kwargs);self.request_budgets=[]
    async def complete(self,*,request_timeout,**kwargs):
        self.request_budgets.append((kwargs['stage'],request_timeout))
        return await super().complete(**kwargs)


def test_gemini_real_async_timeout_cancels_then_fallback_and_synthesis_complete():
    run=reviewed_run();before=copy.deepcopy(run.simulation_response)
    gemini=BudgetAwareFixture(delay=.5);primary=BudgetAwareFixture(delay=.005)
    config=PipelineConfig(total_timeout=3,stage_timeout=.2,critic_timeout=.05,retries=0)
    started=time.monotonic();result=execute(run,primary=primary,critic=gemini,config=config)
    wall=time.monotonic()-started
    assert result.headers['X-Causora-Provider-Mode']=='same-family-fallback'
    assert result.audit['fallbackReason']=='provider_timeout'
    assert 'Critic' in gemini.cancellations
    assert any(stage=='Critic' for stage,_ in primary.events) and primary.events[-1][0]=='Synthesizer'
    assert wall<config.total_timeout<45 and run.simulation_response==before
    events=result.audit['events']
    assert [e['configuredTimeoutSeconds'] for e in events if e['stage']=='Critic']==[.05,.05]
    primary_events=[e for e in events if e['family']=='openai-gpt']
    assert [e['effectiveTimeoutSeconds'] for e in primary_events]==[budget for _,budget in primary.request_budgets]
    assert next(e for e in events if e['family']=='google-gemini')['effectiveTimeoutSeconds']==gemini.request_budgets[0][1]
    target_name=os.getenv('CAUSORA_LOCAL_TIMEOUT_AUDIT_PATH')
    if target_name:
        target=Path(target_name);target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({'kind':'TEST_FIXTURE_ONLY_LOCAL_ASYNC_TIMEOUT_NO_REMOTE_CALLS','wallSeconds':wall,
            'configuredTotalSeconds':3,'configuredCriticSeconds':.05,'frontendSeconds':45,'geminiCancelled':True,
            'fallbackAndSynthesisComplete':True,'simulationUnchanged':True,'events':events},indent=2)+'\n',encoding='utf-8')


def test_remaining_global_budget_shrinks_attempt_before_sdk_and_reserves_following_work():
    async def go():
        config=PipelineConfig(total_timeout=1,stage_timeout=1,critic_timeout=1,retries=0)
        executor=_Execution(config,started=time.monotonic()-.55)
        p=BudgetAwareFixture(delay=.001)
        payload={'allowedMetricRefs':['delta_tco'],'allowedEvidenceIds':[],'allowedOptionIds':['D0','D1','D2']}
        await executor.call(p,'CFO',payload,RoleDraft,timeout=1,reserve=.2)
        event=executor.events[0]
        assert 0<event['effectiveTimeoutSeconds']<.26
        assert event['effectiveTimeoutSeconds']==p.request_budgets[0][1]
        assert event['reservedAfterSeconds']==.2
    asyncio.run(go())


def test_exhausted_wall_budget_does_not_dispatch_any_provider():
    async def go():
        config=PipelineConfig(total_timeout=.1,stage_timeout=1,critic_timeout=1,retries=0)
        executor=_Execution(config,started=time.monotonic()-.2);p=BudgetAwareFixture()
        with pytest.raises(PipelineError) as error:await executor.call(p,'CFO',{},RoleDraft)
        assert error.value.reason=='provider_timeout' and not p.events and executor.calls==0
    asyncio.run(go())


def test_default_config_and_factory_budget_do_not_allow_frontend_deadline_overrun():
    defaults=PipelineConfig();assert (defaults.total_timeout,defaults.stage_timeout,defaults.critic_timeout)==(40,10,15)
    with pytest.raises(ValueError):PipelineConfig(total_timeout=42)


def test_global_timer_cancels_every_already_dispatched_parallel_role():
    async def go():
        executor=_Execution(PipelineConfig(total_timeout=1,stage_timeout=1,critic_timeout=1,retries=0))
        p=BudgetAwareFixture(delay=.5)
        payload={'allowedMetricRefs':['delta_tco'],'allowedEvidenceIds':[],'allowedOptionIds':['D0','D1','D2']}
        calls=[executor.call(p,role,payload,RoleDraft) for role in ('CFO','COO','Risk')]
        with pytest.raises(asyncio.TimeoutError):await asyncio.wait_for(asyncio.gather(*calls),.03)
        assert sorted(p.cancellations)==['CFO','COO','Risk'] and p.active==0
        assert len(p.events)==3 and all(event['status']=='cancelled' for event in executor.events)
    asyncio.run(go())
