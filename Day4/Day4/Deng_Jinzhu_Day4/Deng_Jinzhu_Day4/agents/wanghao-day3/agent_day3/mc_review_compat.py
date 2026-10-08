"""Native Day3 review compatibility; never create approval from pending data.

Current formal format is reviewed_contract.json + review_record.json. Legacy
Day2 approval verification remains available separately; its AI/pending forms
are mapped only to a pending native-format work sheet, never auto-promoted.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys

REQUIRED_ITEMS={'EV-014','EV-019','EV-021','EV-024','EV-027','EV-020',
    'decisionDate','renewalDate','noticeSent','forecastBasis','lockedForecastUnits24m'}
FIELD_PLAN={
    'decisionDate':('ASSUMPTION:decisionDate','demo_data/causora_day1_mock.json',['decisionDate']),
    'renewalDate':('ASSUMPTION:renewalDate','demo_data/causora_day1_mock.json',['renewalDate']),
    'daysToRenewal':('ASSUMPTION:decisionDate','demo_data/causora_day1_mock.json',['decisionDate','renewalDate']),
    'renewalNoticeDays':('EV-014','public/demo/supplier_a_agreement.pdf',['EV-014']),
    'noticeDeadline':('EV-014','public/demo/supplier_a_agreement.pdf',['EV-014','renewalDate']),
    'noticeSent':('ASSUMPTION:noticeSent','public/demo/supplier_correspondence_log.csv',['noticeSent']),
    'noticeRecordSource':('ASSUMPTION:noticeSent','public/demo/supplier_correspondence_log.csv',['noticeSent']),
    'renewalLocked':('EV-020','public/demo/supplier_a_agreement.pdf',['EV-020','EV-014','decisionDate','renewalDate','noticeSent']),
    'renewalTermMonths':('EV-019','public/demo/supplier_a_agreement.pdf',['EV-019']),
    'renewalPriceIncreasePct':('EV-021','public/demo/supplier_a_agreement.pdf',['EV-021']),
    'minPurchaseShareA':('EV-024','public/demo/supplier_a_agreement.pdf',['EV-024']),
    'forecastBasis':('ASSUMPTION:forecastBasis','demo_data/causora_day1_mock.json',['forecastBasis']),
    'lockedForecastUnits24m':('ASSUMPTION:lockedForecastUnits24m','demo_data/causora_day1_mock.json',['lockedForecastUnits24m']),
    'minPurchaseUnitsA':('EV-024','public/demo/supplier_a_agreement.pdf',['EV-024','forecastBasis','lockedForecastUnits24m']),
    'terminationFeeUsd':('EV-027','public/demo/supplier_a_agreement.pdf',['EV-027']),
    'evidenceIds':('EV-020','public/demo/supplier_a_agreement.pdf',['EV-014','EV-019','EV-021','EV-024','EV-027','EV-020']),
}


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def _read(path):
    value=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value,dict): raise ValueError('Review object required')
    return value


def _source(root,relative,digest=None):
    if not isinstance(relative,str) or not relative or Path(relative).is_absolute(): raise ValueError('Relative source path required')
    resolved=(root/relative).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file(): raise ValueError('Review source outside root or unavailable')
    sha=hashlib.sha256(resolved.read_bytes()).hexdigest()
    if digest is not None and sha!=digest: raise ValueError('Review source hash no longer matches')
    return sha


def prepare_pending_native_review(candidate:Path,human_request:Path,backend_root:Path,out:Path):
    """Write deliberately non-verifiable draft filenames/kinds/statuses only."""
    value=_read(candidate); pending=_read(human_request); root=backend_root.resolve()
    rows=pending.get('evidence',[])+pending.get('assumptions',[])
    if {r['id'] for r in rows}!=REQUIRED_ITEMS or len(rows)!=11: raise ValueError('Exact original eleven pending items required')
    if value.get('humanReviewStatus')!='pending' or value.get('decisionReady') is not False:
        raise ValueError('This mapper is only for pending AI candidate data')
    if any(r.get('decision')!='pending' for r in rows) or pending.get('reviewerName') or pending.get('reviewedAtUtc'):
        raise ValueError('Do not reinterpret any supplied completed attestation as a draft')
    if set(value['contract'])!=set(FIELD_PLAN): raise ValueError('Contract field mapping incomplete')
    # Before deriving provenance paths, bind raw source bytes in BOTH owner trees.
    aliases={'demo_data/causora_day1_mock.json':'fixtures/causora_day1_mock.json',
        'public/demo/supplier_a_agreement.pdf':'fixtures/demo/supplier_a_agreement.pdf',
        'public/demo/supplier_correspondence_log.csv':'fixtures/demo/supplier_correspondence_log.csv'}
    hashes={p:_source(root,p,value['sourceHashes'][old]) for p,old in aliases.items()}
    fields={name:{'evidenceId':evidence,'sourceFile':file,'sourceSha256':hashes[file],
        'reviewItemId':deps[0],'derivedFromReviewItemIds':deps,'status':'pending'}
        for name,(evidence,file,deps) in FIELD_PLAN.items()}
    bundle={'kind':'causora.wang.pending-contract-bundle.v1','datasetId':value['datasetId'],
        'dataVersion':value['dataVersion'],'contract':value['contract'],
        'contractSource':{'sourceFile':'public/demo/supplier_a_agreement.pdf','sourceSha256':hashes['public/demo/supplier_a_agreement.pdf']},
        'fieldProvenance':fields,'decisionReady':False,
        'warning':'DRAFT ONLY. ASSUMPTION identifiers are not PDF evidence; derived dependencies need human review.'}
    record={'kind':'causora.wang.review-record.v1','status':'pending','reviewId':'',
        'reviewerRole':'contract_reviewer','reviewerId':'','recordedAtUtc':'',
        'contractPayloadSha256':canonical_sha(bundle['contract']),
        'fieldProvenanceSha256':canonical_sha(fields),
        'reviewedItems':[{'id':r['id'],'status':'pending','confirmedValue':None,'notes':r['notes']} for r in rows],
        'decisionReady':False,'origin':'AI_CANDIDATE_MAPPING_NOT_A_HUMAN_ATTESTATION'}
    if out.exists(): raise FileExistsError('New draft directory required')
    out.mkdir(parents=True)
    for filename,data in [('draft_reviewed_contract.json',bundle),('pending_review_record.json',record)]:
        (out/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return bundle,record


def verify_latest_review_bundle(backend_root:Path,bundle_path:Path):
    """Run actual latest-owner verifier; strengthen eleven-item/source closure.

    An isolated interpreter avoids module collisions with Wang's old Day1 types.
    The result is contract/provenance metadata, NOT an invented DatasetSuccess.
    """
    root=backend_root.resolve(); folder=bundle_path.resolve()
    value=_read(folder/'reviewed_contract.json'); record=_read(folder/'review_record.json')
    if value.get('kind')!='causora.wang.reviewed-contract-bundle.v1' or record.get('status')!='reviewed':
        raise ValueError('Native reviewed record is pending or has an invalid kind')
    if record.get('kind')!='causora.wang.review-record.v1' or not record.get('reviewerId') or not record.get('recordedAtUtc'):
        raise ValueError('Genuine supplied review record is required')
    items=record.get('reviewedItems',[])
    ids={r.get('id') for r in items if r.get('status')=='reviewed'}
    if not REQUIRED_ITEMS<=ids or any(r.get('status')!='reviewed' for r in items): raise ValueError('All eleven exact items must be reviewed')
    if set(value.get('fieldProvenance',{}))!=set(FIELD_PLAN): raise ValueError('Every field requires provenance')
    source=value.get('contractSource',{})
    _source(root,source.get('sourceFile'),source.get('sourceSha256'))
    for entry in value['fieldProvenance'].values():
        if entry.get('reviewItemId') not in ids or not set(entry.get('derivedFromReviewItemIds',[]))<=ids:
            raise ValueError('Field provenance refers to unreviewed items')
        if entry.get('status','reviewed')!='reviewed': raise ValueError('Pending field provenance cannot pass')
        _source(root,entry.get('sourceFile'),entry.get('sourceSha256'))
    verifier=root/'app/release_verifiers.py'
    pins=_read(Path(__file__).resolve().parents[1]/'reference/jinzhu_day3/source_pins.json')
    if hashlib.sha256(verifier.read_bytes()).hexdigest()!=pins['backendFilesSha256']['app/release_verifiers.py']:
        raise ValueError('Latest backend verifier changed; update source baseline explicitly first')
    code="""import sys,json
from pathlib import Path
root=Path(sys.argv[1]); sys.path.insert(0,str(root))
from app.release_verifiers import verify_reviewed_bundle_record
value=verify_reviewed_bundle_record(project_root=root,bundle_path=Path(sys.argv[2]))
print(json.dumps(dict(value),ensure_ascii=False,allow_nan=False))
"""
    result=subprocess.run([sys.executable,'-X','utf8','-I','-c',code,str(root),str(folder)],capture_output=True,text=True,encoding='utf-8',timeout=30)
    if result.returncode: raise ValueError('Latest original backend review verifier rejected the supplied native bundle')
    checked=json.loads(result.stdout)
    if checked['contractPayloadSha256']!=canonical_sha(value['contract']): raise ValueError('Contract digest differs')
    return checked
