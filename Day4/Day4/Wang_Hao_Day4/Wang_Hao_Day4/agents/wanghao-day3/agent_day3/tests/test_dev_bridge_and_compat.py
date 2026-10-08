import copy
import hashlib
import json
import os
from pathlib import Path
import pytest
from agent_day3.dev_bridge import build_development_bundle,verify_development_bundle,source_mapping,candidate,write_development_bundle
from agent_day3.projections import verify_human_review_bundle
from agent_day3.review_compat import verify_legacy_review_bundle,convert_verified_legacy_bundle
from agent_day3.wire_models import DatasetSuccessEnvelope
from agent_day3.tests.test_day3 import local_snapshot,review_bundle


@pytest.fixture(scope='module')
def root():
    value=os.getenv('CAUSORA_JINZHU_ROOT')
    if not value: pytest.skip('External Jinzhu workspace required; set CAUSORA_JINZHU_ROOT explicitly')
    return Path(value).resolve()


@pytest.fixture(scope='module')
def bundle(root): return build_development_bundle(root,enabled=True)


def test_explicit_dev_enable_required(root):
    with pytest.raises(ValueError,match='Explicit'): build_development_bundle(root)


def test_actual_bundle_source_and_version_are_bound(root,bundle):
    audit=verify_development_bundle(bundle,root,enabled=True)
    assert audit['matrixCells']==9 and audit['traceRows']==936
    assert bundle['preview']['reviewStatus']=='PENDING_HUMAN_REVIEW'
    assert bundle['lineage']['candidateDataVersion']!=bundle['lineage']['engineSourceDataVersion']
    assert bundle['preview']['sourceDataVersion']==bundle['lineage']['engineSourceDataVersion']
    assert bundle['sourceMode']=='UNREVIEWED_DEV_COMPUTED'
    assert 'cashOutflowP90' not in bundle['preview']['matrix']['baseline'][0]
    assert 'stockoutProbability' not in bundle['preview']['matrix']['baseline'][0]


@pytest.mark.parametrize('field,value',[('decisionReady',True),('humanReviewStatus','approved'),('sourceMode','SIMULATION_READY')])
def test_no_status_promotion(root,bundle,field,value):
    bad=copy.deepcopy(bundle); bad[field]=value
    with pytest.raises(ValueError): verify_development_bundle(bad,root,enabled=True)


def test_edited_preview_with_same_id_rejected(root,bundle):
    bad=copy.deepcopy(bundle); bad['preview']['matrix']['demand-drop'][1]['cashOutflowUsd']+=1
    with pytest.raises(ValueError): verify_development_bundle(bad,root,enabled=True)


def test_lineage_version_edit_rejected(root,bundle):
    bad=copy.deepcopy(bundle); bad['lineage']['engineSourceDataVersion']=bad['lineage']['candidateDataVersion']
    with pytest.raises(ValueError,match='lineage'): verify_development_bundle(bad,root,enabled=True)


def test_wrong_cross_owner_source_digest_rejected(root):
    value=candidate(); value['sourceHashes']['fixtures/demo/historical_demand.csv']='0'*64
    with pytest.raises(ValueError,match='Cross-owner'): source_mapping(value,root)


def test_dev_manifest_not_formal_bundle(tmp_path,bundle):
    out=tmp_path/'dev'; write_development_bundle(bundle,out)
    assert not (out/'bundle_manifest.json').exists() and not (out/'human_receipt.json').exists()
    assert not (out/'jinzhu_contract_input.json').exists()
    with pytest.raises(ValueError,match='missing required'): verify_human_review_bundle(out)
    with pytest.raises(FileExistsError): write_development_bundle(bundle,out)


def test_pending_legacy_cannot_convert_or_pass(root,tmp_path):
    pending=root/'evidence_day2/examples/pending_review'
    with pytest.raises(ValueError,match='incomplete'): verify_legacy_review_bundle(root,pending)
    with pytest.raises(ValueError): convert_verified_legacy_bundle(root,pending,tmp_path/'should-not-exist')
    assert not (tmp_path/'should-not-exist').exists()


def test_legacy_format_needs_explicit_root(tmp_path):
    (tmp_path/'bundle_manifest.json').write_text('{}\n',encoding='utf-8')
    with pytest.raises(ValueError,match='explicit'): verify_human_review_bundle(tmp_path)


def test_legacy_dispatch_does_not_bypass_original_verifier(tmp_path,monkeypatch):
    (tmp_path/'bundle_manifest.json').write_text('{}\n',encoding='utf-8')
    def reject(*args): raise ValueError('original checker rejected')
    monkeypatch.setattr('agent_day3.review_compat.verify_legacy_review_bundle',reject)
    with pytest.raises(ValueError,match='original checker'): verify_human_review_bundle(tmp_path,legacy_project_root=tmp_path)


def test_conversion_preserves_existing_review_identity_and_version(tmp_path,monkeypatch):
    # Pure wrapper test with a verifier test double. Never a supplied human review.
    old=review_bundle(tmp_path,local_snapshot())
    raw=json.loads((old/'dataset_success.json').read_text(encoding='utf-8'))
    parsed=DatasetSuccessEnvelope.model_validate(raw)
    receipt={'reviewerName':'TEST_DOUBLE_NOT_REAL_HUMAN','reviewedAtUtc':'2026-10-04T00:00:00Z',
        'sourceHashes':{'supplier_a_agreement.pdf':'a'*64},
        'approvedEvidenceIds':['EV-014','EV-019','EV-021','EV-024','EV-027','EV-020'],
        'approvedAssumptionKeys':['decisionDate','renewalDate','noticeSent','forecastBasis','lockedForecastUnits24m']}
    (old/'review_receipt.json').write_text(json.dumps(receipt),encoding='utf-8')
    (old/'bundle_manifest.json').write_text('{"TEST_DOUBLE_ONLY":true}\n',encoding='utf-8')
    monkeypatch.setattr('agent_day3.review_compat.verify_legacy_review_bundle',lambda *args:parsed)
    out=tmp_path/'converted-test-double'; convert_verified_legacy_bundle(tmp_path,old,out)
    result=json.loads((out/'human_receipt.json').read_text(encoding='utf-8'))
    assert result['reviewerName']==receipt['reviewerName'] and result['reviewedAtUtc']==receipt['reviewedAtUtc']
    assert verify_human_review_bundle(out).dataVersion==parsed.dataVersion
    assert json.loads((out/'legacy_provenance.json').read_text(encoding='utf-8'))['dataVersionUnchanged']==parsed.dataVersion
