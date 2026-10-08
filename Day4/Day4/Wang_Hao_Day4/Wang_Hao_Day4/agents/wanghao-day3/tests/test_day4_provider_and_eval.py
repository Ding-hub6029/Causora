import asyncio,json
from pathlib import Path
import pytest
from agent_day4.provider import CallBudget,ProviderFailure,LiveProvider
from agent_day4.eval_interface import load_blind_inputs,prediction_record,case_identifier,model_payload


def test_shared_request_budget_is_atomic_across_concurrent_stages():
    async def check():
        budget=CallBudget(3)
        results=await asyncio.gather(*(budget.acquire() for _ in range(8)),return_exceptions=True)
        assert budget.used==3 and sum(isinstance(v,ProviderFailure) for v in results)==5
    asyncio.run(check())


def test_no_implicit_model_or_credentials(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    with pytest.raises(ProviderFailure,match='provider_not_configured'):LiveProvider('gpt-5-mini')
    with pytest.raises(ValueError):CallBudget(13)


def test_existing_heldout_inputs_are_loaded_without_labels_import():
    directory=Path(__file__).resolve().parents[1]/'agent_day3/evals'
    path=directory/'critic_heldout_inputs.jsonl'
    records=load_blind_inputs(path)
    assert records and len({case_identifier(r) for r in records})==len(records)
    assert 'caseId' not in model_payload(records[0])
    record=prediction_record(case_id=case_identifier(records[0]),input_record=records[0],issues=[],provider='TEST_FIXTURE_ONLY',model='TEST_FIXTURE_ONLY',run_id='not-a-score')
    assert record['evaluationStatus']=='UNSCORED_HELDOUT_PREDICTION' and record['humanLabelsApproved'] is False
    assert set(record['scorerRow'])=={'caseId','inputSha256','status','faultDetected'}


def test_blind_loader_rejects_nested_answers_and_duplicate_ids(tmp_path):
    path=tmp_path/'cases.jsonl'
    path.write_text(json.dumps({'id':'neutral','facts':{'labels':['answer']}})+'\n',encoding='utf-8')
    with pytest.raises(ValueError,match='answer/label'):load_blind_inputs(path)
    path.write_text('{"id":"neutral"}\n{"id":"neutral"}\n',encoding='utf-8')
    with pytest.raises(ValueError,match='Duplicate'):load_blind_inputs(path)
