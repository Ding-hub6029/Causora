"""Explicit pending-review development bridge to Jinzhu's actual deterministic engine.
Never exports SimulationResult or probability/P90 fields; original versions are retained.
"""
from __future__ import annotations
import hashlib
import importlib
import json
from pathlib import Path
import sys
from .wire_models import ContractConstraint,EvidenceRecord,read_json_object,sha256_json
from .dev_trace_validation import audit_deterministic_preview

ROOT=Path(__file__).resolve().parents[1]
SOURCE_MAP={
 'fixtures/causora_day1_mock.json':'demo_data/causora_day1_mock.json',
 'fixtures/demo/historical_demand.csv':'public/demo/historical_demand.csv',
 'fixtures/demo/opening_inventory.csv':'public/demo/opening_inventory.csv',
 'fixtures/demo/supplier_a_agreement.pdf':'public/demo/supplier_a_agreement.pdf',
 'fixtures/demo/supplier_correspondence_log.csv':'public/demo/supplier_correspondence_log.csv',
 'fixtures/demo/supplier_delivery_history.xlsx':'public/demo/supplier_delivery_history.xlsx',
 'reference/API_CONTRACT.md':'API_CONTRACT.md','reference/contracts.ts':'lib/contracts.ts'}


def candidate(path:Path|None=None):
    from evidence_review.pipeline import build
    value=read_json_object(path or ROOT/'evidence_review/data/reviewed_data.json')
    expected=build()['reviewed_data.json']
    if value!=expected or value.get('decisionReady') is not False or value.get('humanReviewStatus')!='pending':
        raise ValueError('Only the exact current pending AI candidate is permitted for development')
    ContractConstraint.model_validate(value['contract'])
    records=[EvidenceRecord.model_validate(e) for e in value['evidence']]
    if [e.id for e in records]!=value['contract']['evidenceIds'] or not all(e.quoteMatched for e in records):
        raise ValueError('Development evidence does not match its typed contract')
    return value


def _load_engine(root:Path):
    root=root.resolve()
    sys.path.insert(0,str(root))
    try: module=importlib.import_module('simulation_day2.deterministic')
    finally: sys.path.remove(str(root))
    if not Path(module.__file__).resolve().is_relative_to(root):
        raise ValueError('A different Jinzhu project is already imported; start a fresh process with the requested root')
    return module


def source_mapping(value:dict,root:Path):
    result={}
    if set(value['sourceHashes'])!=set(SOURCE_MAP): raise ValueError('Candidate source set changed')
    for alias,relative in SOURCE_MAP.items():
        path=(root/relative).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file(): raise ValueError('Missing or unsafe backend source')
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if value['sourceHashes'][alias]!=actual: raise ValueError('Cross-owner source mismatch: '+relative)
        result[alias]={'backendPath':relative,'sha256':actual}
    raw=read_json_object(root/'demo_data/causora_day1_mock.json')
    if value['contract']!=raw['contract']: raise ValueError('Candidate contract differs from the actual development engine input')
    return result


def _lineage(value,preview,request,policy,mapping,audit):
    record={'kind':'CAUSORA_UNREVIEWED_DEVELOPMENT_LINEAGE_V1',
        'candidateDataVersion':value['dataVersion'],'candidateScopeSha256':value['scopeSha256'],
        'candidateSha256':sha256_json(value),'engineSourceDataVersion':preview['sourceDataVersion'],
        'previewId':preview['previewId'],'previewSha256':sha256_json(preview),
        'requestSha256':sha256_json(request),'policySha256':sha256_json(policy),
        'contractSha256':sha256_json(value['contract']),'evidenceSha256':sha256_json(value['evidence']),
        'traceAuditSha256':sha256_json(audit),
        'sourceHashMapping':mapping,
        'engineSourceSha256':preview['engineSourceSha256'],
        'intermediateManifestSha256':preview['intermediateManifestSha256'],
        'traceAuditorSha256':hashlib.sha256((ROOT/'agent_day3/dev_trace_validation.py').read_bytes()).hexdigest(),
        'versionRelationship':'DISTINCT_VERSIONS_SAME_RAW_SOURCE_BYTES_AND_CONTRACT; ENGINE_VERSION_NOT_REWRITTEN',
        'humanReviewStatus':'pending','policyReviewStatus':'UNAPPROVED_TEST_INPUT','decisionReady':False}
    record['analysisDataVersion']='dev-analysis-'+sha256_json(record)[:20]
    return record


def build_development_bundle(jinzhu_root:Path,*,enabled:bool=False,candidate_path:Path|None=None,
                             request:dict|None=None,policy:dict|None=None):
    if enabled is not True: raise ValueError('Explicit unreviewed development configuration is required')
    root=jinzhu_root.resolve(); value=candidate(candidate_path)
    mapping=source_mapping(value,root)
    request=request if request is not None else read_json_object(root/'simulation_day1/examples/simulate_request.json')
    policy=policy if policy is not None else read_json_object(root/'simulation_day2/examples/UNAPPROVED_TEST_POLICY.json')
    preview=_load_engine(root).run_unreviewed_preview(request,policy,project_root=root)
    audit=audit_deterministic_preview(preview,request,policy,value['contract'],root)
    lineage=_lineage(value,preview,request,preview['policy'],mapping,audit)
    return {'kind':'CAUSORA_UNREVIEWED_DEVELOPMENT_BUNDLE_V1','humanReviewStatus':'pending',
        'permittedUse':'DEVELOPMENT_TEST_ONLY','sourceMode':'UNREVIEWED_DEV_COMPUTED','decisionReady':False,
        'preview':preview,'request':request,'contract':value['contract'],'evidence':value['evidence'],
        'traceAudit':audit,'lineage':lineage,
        'warning':'Actually computed deterministic development preview on synthetic sources and an unapproved policy; NOT public SimulationResult, MC statistics, human approval or recommendation.'}


def verify_development_bundle(bundle:dict,jinzhu_root:Path,*,enabled:bool=False,candidate_path:Path|None=None):
    if enabled is not True: raise ValueError('Development verification must be explicitly enabled')
    if bundle.get('kind')!='CAUSORA_UNREVIEWED_DEVELOPMENT_BUNDLE_V1' or bundle.get('decisionReady') is not False or bundle.get('humanReviewStatus')!='pending':
        raise ValueError('Development bundle cannot be promoted by changing flags')
    value=candidate(candidate_path); mapping=source_mapping(value,jinzhu_root.resolve())
    if bundle['contract']!=value['contract'] or bundle['evidence']!=value['evidence']:
        raise ValueError('Bundle candidate fields changed')
    preview=bundle['preview']; request=bundle['request']; policy=preview['policy']
    audit=audit_deterministic_preview(preview,request,policy,value['contract'],jinzhu_root)
    if bundle['traceAudit']!=audit or bundle['lineage']!=_lineage(value,preview,request,policy,mapping,audit):
        raise ValueError('Trace audit/version/lineage digest mismatch')
    if bundle.get('permittedUse')!='DEVELOPMENT_TEST_ONLY' or bundle.get('sourceMode')!='UNREVIEWED_DEV_COMPUTED':
        raise ValueError('Development-only use labels were altered')
    return audit


def write_development_bundle(bundle:dict,out:Path):
    if out.exists(): raise FileExistsError('New output directory required')
    out.mkdir(parents=True)
    artifacts={'development_bundle.json':bundle,'computed_deterministic_preview_UNREVIEWED.json':bundle['preview'],
        'trace_audit.json':bundle['traceAudit'],'lineage.json':bundle['lineage'],'simulate_request.json':bundle['request'],
        'UNAPPROVED_TEST_POLICY.json':bundle['preview']['policy']}
    for name,value in artifacts.items():
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    manifest={'kind':'CAUSORA_UNREVIEWED_DEVELOPMENT_MANIFEST_V1','decisionReady':False,
              'humanReviewStatus':'pending','filesSha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in artifacts}}
    (out/'development_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest
