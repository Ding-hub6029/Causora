import json
import os
from pathlib import Path
import threading
import urllib.error
import urllib.request
import pytest
from agent_day3.dev_http import make_server


@pytest.fixture(scope='module')
def server():
    value=os.getenv('CAUSORA_JINZHU_ROOT')
    if not value: pytest.skip('Explicit external Jinzhu workspace needed for HTTP integration')
    http=make_server(Path(value),enabled=True)
    thread=threading.Thread(target=http.serve_forever,daemon=True); thread.start()
    yield http
    http.shutdown(); http.server_close(); thread.join(timeout=3)


def exchange(server,path,body=None):
    headers={'Content-Type':'application/json'}
    req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}'+path,
        data=json.dumps(body).encode() if body is not None else None,headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=10) as response: return response.status,json.load(response)
    except urllib.error.HTTPError as error: return error.code,json.load(error)


def test_server_is_not_implicitly_enabled(tmp_path):
    with pytest.raises(PermissionError): make_server(tmp_path)


def test_development_health_cannot_claim_formal_ready(server):
    status,value=exchange(server,'/dev/health')
    assert status==200 and value['formalSimulateSuccessAvailable'] is False
    assert value['humanReviewStatus']=='pending' and value['decisionReady'] is False


def test_real_engine_computation_over_http(server):
    status,value=exchange(server,'/dev/compute',{})
    assert status==200 and value['traceAudit']['traceRows']==936
    assert value['preview']['previewId'].startswith('preview-day2-')
    assert value['preview']['monteCarloRuns']==0 and value['decisionReady'] is False


def test_actual_three_role_development_analysis_over_http(server):
    status,value=exchange(server,'/dev/analyse',{'scenarioId':'demand-drop'})
    assert status==200 and value['state']=='ALL_READY'
    assert [row['role'] for row in value['outputs']]==['CFO','COO','Risk']
    assert {row['availability'] for row in value['outputs']}=={'DEV_ONLY'}
    assert value['decisionReady'] is False and value['providerKind']=='OFFLINE_STUB'
    assert 'coo_purchases_exceed_demand' in value['outputs'][1]['claimIds']
    assert 'coo_purchases_equal_demand' not in value['outputs'][1]['claimIds']


def test_original_formal_api_still_refuses_unreviewed_data(server):
    root=Path(os.environ['CAUSORA_JINZHU_ROOT'])
    request=json.loads((root/'simulation_day1/examples/simulate_request.json').read_text(encoding='utf-8'))
    status,value=exchange(server,'/api/simulate',request)
    assert status==503 and value['error']['code']=='simulation_failed'
    assert value['error']['details']['reason']=='human_review_pending'
    assert 'data' not in value


@pytest.mark.parametrize('body',[{'scenarioId':'invalid'},{'humanReviewStatus':'approved'},{'request':{'wrong':True}}])
def test_development_http_rejects_bad_inputs_without_source_leak(server,body):
    status,value=exchange(server,'/dev/analyse',body)
    assert status==400 and value['code']=='DEV_INPUT_OR_SOURCE_INVALID'
    assert '/home/' not in json.dumps(value) and 'Traceback' not in json.dumps(value)


def test_production_boardroom_is_not_fabricated(server):
    status,value=exchange(server,'/api/boardroom',{})
    assert status==404 and 'agentOutputs' not in value
