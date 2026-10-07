import copy
import json
import os
from pathlib import Path
import pytest
from agent_day3.mc_client import load_capture,post_simulation
from agent_day3.mc_validation import validate_mc_response
from agent_day3.mc_review_compat import prepare_pending_native_review,verify_latest_review_bundle,REQUIRED_ITEMS
ROOT=Path(__file__).resolve().parents[2]


def load(name='http_base'):
    path=ROOT/'mc_examples'/name
    return {key:json.loads((path/(key+'.json')).read_text(encoding='utf-8')) for key in ('request','response','transport')}


def test_real_capture_is_bound_and_validated():
    cap=load_capture(ROOT/'mc_examples/http_base')
    assert cap['audit']['matrixCells']==9 and cap['audit']['sampleWeeks']==936
    assert cap['response']['data']['simulation']['monteCarloRuns']==1000


def test_client_must_be_explicitly_enabled():
    with pytest.raises(PermissionError): post_simulation('http://127.0.0.1:1',load()['request'])


@pytest.mark.parametrize('key,value',[('schemaVersion','causora.contract.v2'),('datasetId','other'),('seed',True)])
def test_bad_v1_request_is_rejected(key,value):
    cap=load();cap['request'][key]=value
    with pytest.raises(ValueError):validate_mc_response(cap['request'],cap['response'])


def test_missing_trace_anchor_is_clean_valueerror():
    cap=load();del cap['response']['data']['traces']['baseline']['D0']
    with pytest.raises(ValueError): validate_mc_response(cap['request'],cap['response'])


def test_different_cell_policy_identity_is_rejected():
    cap=load();cap['response']['data']['traces']['lead-stress']['D1']['runIdentity']['policySha256']='0'*64
    with pytest.raises(ValueError): validate_mc_response(cap['request'],cap['response'])


def test_string_boolean_contract_state_is_rejected():
    cap=load()
    for by_scenario in cap['response']['data']['traces'].values():
        for trace in by_scenario.values():
            for param in trace['parameters']:
                if param['key']=='contract.renewalLocked':param['value']='false'
    with pytest.raises(ValueError):validate_mc_response(cap['request'],cap['response'])


def test_contract_provenance_cannot_be_observed_or_approved():
    cap=load()
    for by_scenario in cap['response']['data']['traces'].values():
        for trace in by_scenario.values():
            for param in trace['parameters']:
                if param['key'].startswith('contract.'):
                    param['provenance']['kind']='observed_synthetic_dataset';param['provenance']['status']='observed'
    with pytest.raises(ValueError): validate_mc_response(cap['request'],cap['response'])


def test_changed_request_does_not_reuse_capture(tmp_path):
    import shutil
    out=tmp_path/'capture';shutil.copytree(ROOT/'mc_examples/http_base',out)
    path=out/'request.json';value=json.loads(path.read_text(encoding='utf-8'));value['budgetCeilingUsd']+=1
    path.write_text(json.dumps(value),encoding='utf-8')
    with pytest.raises(ValueError): load_capture(out)


def test_pending_native_draft_never_names_a_signed_bundle():
    path=ROOT/'evidence_review/data/native_day3_pending'
    assert not (path/'reviewed_contract.json').exists() and not (path/'review_record.json').exists()
    value=json.loads((path/'pending_review_record.json').read_text(encoding='utf-8'))
    assert value['status']=='pending' and not value['reviewerId'] and not value['recordedAtUtc']
    assert {i['id'] for i in value['reviewedItems']}==REQUIRED_ITEMS
    assert {i['status'] for i in value['reviewedItems']}=={'pending'}


def test_renaming_pending_draft_cannot_pass_native_verifier(tmp_path):
    import shutil
    path=ROOT/'evidence_review/data/native_day3_pending'
    shutil.copyfile(path/'draft_reviewed_contract.json',tmp_path/'reviewed_contract.json')
    shutil.copyfile(path/'pending_review_record.json',tmp_path/'review_record.json')
    with pytest.raises(ValueError):verify_latest_review_bundle(tmp_path,tmp_path)


def test_pending_draft_reproducible_with_latest_backend(tmp_path):
    env=os.getenv('CAUSORA_DAY3_BACKEND')
    if not env: pytest.skip('Original latest backend is required for source-file verification')
    bundle,record=prepare_pending_native_review(ROOT/'evidence_review/data/reviewed_data.json',ROOT/'evidence_review/data/human_review_request.json',Path(env),tmp_path/'draft')
    assert set(bundle['fieldProvenance'])==set(bundle['contract'])
    assert all(item['status']=='pending' for item in record['reviewedItems'])
    assert record['status']=='pending'


def test_current_original_native_verifier_rejects_the_draft(tmp_path):
    env=os.getenv('CAUSORA_DAY3_BACKEND')
    if not env:pytest.skip('Latest original backend verifier required')
    import subprocess,sys,shutil
    source=ROOT/'evidence_review/data/native_day3_pending'
    for original,renamed in [('draft_reviewed_contract.json','reviewed_contract.json'),('pending_review_record.json','review_record.json')]:
        shutil.copyfile(source/original,tmp_path/renamed)
    code='import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from app.release_verifiers import verify_reviewed_bundle_record;verify_reviewed_bundle_record(project_root=Path(sys.argv[1]),bundle_path=Path(sys.argv[2]))'
    result=subprocess.run([sys.executable,'-I','-c',code,env,str(tmp_path)],capture_output=True,timeout=30)
    assert result.returncode!=0
    assert b'Reviewed bundle kind or datasetId is invalid' in result.stderr


def test_supplied_human_review_survives_windows_non_utf8_parent(monkeypatch):
    env = os.getenv('CAUSORA_DAY3_BACKEND')
    if not env: pytest.skip('Integrated backend is required')
    root = Path(env)
    folder = root / 'reviewed/wang-2026-10-07'
    if not folder.is_dir(): pytest.skip('Supplied human confirmation is not part of this standalone backend')
    monkeypatch.setenv('PYTHONUTF8', '0')
    checked = verify_latest_review_bundle(root, folder)
    assert checked['reviewReference'] == 'wang-supplied-confirmation-2026-10-07'
    assert checked['contract']['noticeSent'] is False
