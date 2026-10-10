from pathlib import Path
import copy
import json
import shutil
import pytest
from evidence_review.pipeline import ROOT, ASSUMPTIONS, EVIDENCE_IDS, build, derive, check_sources, main


def test_six_evidence_and_five_assumptions():
    outputs=build()
    ledger=outputs['review_ledger.json']
    assert len(ledger['items'])==11
    assert all(i['syntheticDecision']=='reviewed_synthetic' for i in ledger['items'])
    assert all(i['humanDecision']=='pending' and i['realWorldVerification']=='not_verified' for i in ledger['items'])
    assert [i['id'] for i in ledger['items']]==list(EVIDENCE_IDS+ASSUMPTIONS)


def test_no_human_or_live_claim():
    out=build(); c=out['reviewed_data.json']; e=out['evidence_summary.json']
    assert c['decisionReady'] is False and c['sourceMode']=='LOCAL_MOCK'
    assert c['humanReviewStatus']=='pending' and c['simulationState']=='NOT_COMPUTED'
    assert 'simulation' not in c and 'brief' not in c and 'preprocessStatus' not in c
    assert all(not r['manually_verified'] for r in e['records'])
    assert not e['business_variables']
    assert all(r['quote_matched'] and r['page']==4 and r['locator_bbox'] for r in e['records'])
    request=out['human_review_request.json']
    assert request['reviewerName']==request['reviewedAtUtc']==''
    assert all(r['decision']=='pending' and r['confirmedValue'] is None for g in ['evidence','assumptions'] for r in request[g])


def test_typed_wire_units_and_internal_sixth():
    out=build(); c=out['reviewed_data.json']
    assert c['contract']['renewalPriceIncreasePct']==0.14
    assert c['contract']['minPurchaseShareA']==0.6
    assert type(c['contract']['terminationFeeUsd']) is int
    assert len(c['evidence'])==5 and len(c['variables'])==5
    assert 'EV-020' not in c['contract']['evidenceIds']
    assert c['conditionalAutoRenewEvidenceId']=='EV-020'
    assert {r['id'] for r in out['evidence_summary.json']['records']}==set(EVIDENCE_IDS)
    assert c['dataVersion']!=c['baselineDataVersion']
    assert all(e['matchScore']==1.0 and len(e['locatorBbox'])==4 for e in c['evidence'])


def test_values_and_conditional_derivations():
    c=build()['reviewed_data.json']['contract']
    assert derive(c)=={'daysToRenewal':45,'noticeDeadline':'2026-09-19','renewalLocked':True,'minPurchaseUnitsA':15600}
    c=copy.deepcopy(c); c['noticeSent']=True
    assert derive(c)['renewalLocked'] is False
    c['noticeSent']=False; c['decisionDate']='2026-09-19'
    assert derive(c)['renewalLocked'] is False


def test_reproducible():
    assert build()==build()


def test_source_tamper_rejected(tmp_path):
    root=tmp_path/'pack'; shutil.copytree(ROOT/'reference',root/'reference')
    shutil.copytree(ROOT/'fixtures',root/'fixtures')
    (root/'fixtures/demo/supplier_a_agreement.pdf').write_bytes(b'fake')
    with pytest.raises(ValueError,match='Frozen source changed'): check_sources(root)


def test_wrong_reviewer_value_stays_pending():
    raw=json.loads((ROOT/'reference/review_findings_raw.json').read_text(encoding='utf-8'))
    next(r for r in raw['items'] if r['id']=='noticeSent')['valueJson']='"false"'
    result=build(findings=raw)
    row=next(i for i in result['review_ledger.json']['items'] if i['id']=='noticeSent')
    assert row['syntheticDecision']=='pending'
    assert row['value'] is False
    assert row['humanDecision']=='pending'


@pytest.mark.parametrize('mode',['missing','duplicate','failed'])
def test_incomplete_research_is_not_complete(mode):
    raw=json.loads((ROOT/'reference/review_findings_raw.json').read_text(encoding='utf-8'))
    if mode=='missing': raw['items'].pop()
    elif mode=='duplicate': raw['items'][-1]=raw['items'][0]
    else: raw['failures']=[{'id':'noticeSent','error':'unavailable'}]
    with pytest.raises(ValueError): build(findings=raw)


def test_cli_new_directory_only(tmp_path,monkeypatch):
    import sys
    out=tmp_path/'out'
    monkeypatch.setattr(sys,'argv',['review','--out',str(out)])
    main(); assert len(list(out.glob('*.json')))==4
    with pytest.raises(FileExistsError): main()
