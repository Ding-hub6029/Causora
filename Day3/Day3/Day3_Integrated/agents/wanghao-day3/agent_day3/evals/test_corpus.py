import copy
import hashlib
from pathlib import Path
import pytest
from .build_fixtures import build, canonical
from .scoring import score, prompt_payload


def data(tmp_path):
    dev,inputs,labels=build(tmp_path)
    predictions=[{'caseId':r['caseId'],'inputSha256':r['inputSha256'],'status':'ok','faultDetected':False} for r in labels]
    return dev,inputs,labels,predictions


def test_split_sizes_opaque_ids_and_mixed_order(tmp_path):
    dev,inputs,labels,_=data(tmp_path)
    assert len(dev)==12 and sum(c['expected']['faulty'] for c in dev)==8
    assert len(inputs)==30 and sum(c['expected']['faulty'] for c in labels)==20
    assert len({r['caseId'] for r in inputs})==30
    assert not ({r['caseId'] for r in dev}&{r['caseId'] for r in inputs})
    assert all(r['caseId'].startswith('h') and len(r['caseId'])==4 for r in inputs)
    flags=[r['expected']['faulty'] for r in labels]
    assert flags!=sorted(flags) and flags!=sorted(flags,reverse=True)


def test_input_only_and_full_fact_packet(tmp_path):
    _,inputs,labels,_=data(tmp_path)
    for row,label in zip(inputs,labels):
        assert set(row)=={'caseId','split','source','input'}
        payload=prompt_payload(row)
        assert payload==row['input']
        assert 'caseId' not in payload and 'labelStatus' not in payload
        facts=payload['frozenMockFacts']
        assert facts['sourceMode']=='LOCAL_MOCK'
        assert facts['contract']['forecastBasis']=='locked-at-renewal'
        assert len(facts['options'])==len(facts['cells'])==3
        assert len(facts['evidence'])==5
        assert label['inputSha256']==hashlib.sha256(canonical(row)).hexdigest()


def test_deterministic_and_no_identical_whole_inputs(tmp_path):
    a=build(tmp_path/'a'); b=build(tmp_path/'b'); assert a==b
    dev,inputs,_,_=data(tmp_path/'c')
    assert not ({canonical(r['input']) for r in dev}&{canonical(r['input']) for r in inputs})
    # Shared taxonomy/motifs remain; exact disjointness is not semantic independence.


def test_model_loader_rejects_answer_fields(tmp_path):
    _,inputs,_,_=data(tmp_path)
    row=copy.deepcopy(inputs[0]); row['input']['expected']={'faulty':True}
    with pytest.raises(ValueError,match='Answer-bearing'): prompt_payload(row)
    row=copy.deepcopy(inputs[0]); row['expected']=True
    with pytest.raises(ValueError): prompt_payload(row)


def test_draft_cannot_produce_official_score(tmp_path):
    _,i,l,p=data(tmp_path)
    with pytest.raises(ValueError,match='draft labels'): score(i,l,p)


def test_recall_precision_false_positive_math(tmp_path):
    _,i,l,p=data(tmp_path)
    faults=[r for r in l if r['expected']['faulty']]; clean=[r for r in l if not r['expected']['faulty']]
    detect={r['caseId'] for r in faults[:10]+clean[:2]}
    for row in p: row['faultDetected']=row['caseId'] in detect
    result=score(i,l,p,draft_rehearsal=True)
    assert result['truePositive']==10 and result['falseNegative']==10
    assert result['falsePositiveCount']==2 and result['trueNegative']==8
    assert result['recall']==0.5 and result['precision']==10/12
    assert result['kind']=='DRAFT_HARNESS_REHEARSAL_NOT_CRITIC_PERFORMANCE'


def test_timeouts_not_silently_dropped(tmp_path):
    _,i,l,p=data(tmp_path)
    target=next(r['caseId'] for r in l if not r['expected']['faulty'])
    row=next(r for r in p if r['caseId']==target); row.update(status='timeout',faultDetected=None)
    result=score(i,l,p,draft_rehearsal=True)
    assert result['status']=='incomplete' and result['failedCleanControls']==1
    assert result['trueNegative']==9 and result['falseNegative']==20
    with pytest.raises(ValueError,match='Missing'): score(i,l,p[:-1],draft_rehearsal=True)


def test_digest_duplicates_unknown_fields_rejected(tmp_path):
    _,i,l,p=data(tmp_path)
    bad=copy.deepcopy(p); bad[0]['inputSha256']='0'*64
    with pytest.raises(ValueError,match='digest'): score(i,l,bad,draft_rehearsal=True)
    with pytest.raises(ValueError,match='Duplicate'): score(i,l,p+[p[0]],draft_rehearsal=True)
    bad=copy.deepcopy(p); bad[0]['extra']=True
    with pytest.raises(ValueError,match='Unexpected'): score(i,l,bad,draft_rehearsal=True)
