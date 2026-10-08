"""Legacy Day2 is the common formal review format; no synthetic self-signing.

Jinzhu keeps bundle_manifest.json + jinzhu_contract_input.json. Wang can consume
that exact bundle via its original verifier, or wrap it as the existing v3 gate.
Pending candidate data cannot be converted into an approved bundle.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
from .wire_models import DatasetSuccessEnvelope,HumanReceipt,ReviewScope,read_json_object,sha256_json

EVIDENCE={'EV-014','EV-019','EV-021','EV-024','EV-027','EV-020'}
ASSUMPTIONS={'decisionDate','renewalDate','noticeSent','forecastBasis','lockedForecastUnits24m'}


def verify_legacy_review_bundle(project_root:Path,bundle:Path)->DatasetSuccessEnvelope:
    root=project_root.resolve(); folder=bundle.resolve()
    required={'bundle_manifest.json','jinzhu_contract_input.json','dataset_success.json',
              'approved_review.json','review_receipt.json','review_scope.json','reviewed_evidence_summary.json'}
    if not root.is_dir() or not (root/'evidence_day2/cli.py').is_file():
        raise ValueError('Explicit combined legacy project root is required')
    if any(not (folder/name).is_file() for name in required):
        raise ValueError('Legacy review bundle is incomplete; pending review cannot pass')
    # Use an isolated interpreter: imported Day1/Wang modules cannot leak in from
    # another project path. Original verify_bundle repeats source/scope/promotion.
    code="""import sys,json
from pathlib import Path
root=Path(sys.argv[1]); bundle=Path(sys.argv[2]); sys.path.insert(0,str(root))
from evidence_day2.cli import verify_bundle
verify_bundle(root,bundle)
"""
    result=subprocess.run([sys.executable,'-I','-c',code,str(root),str(folder)],capture_output=True,text=True,encoding='utf-8',timeout=30)
    if result.returncode:
        raise ValueError('Original Day2 verifier rejected review/source/code/version; no human approval inferred')
    raw=read_json_object(folder/'dataset_success.json')
    dataset=DatasetSuccessEnvelope.model_validate(raw)
    receipt=read_json_object(folder/'review_receipt.json')
    handoff=read_json_object(folder/'jinzhu_contract_input.json')
    if set(receipt['approvedEvidenceIds'])!=EVIDENCE or set(receipt['approvedAssumptionKeys'])!=ASSUMPTIONS:
        raise ValueError('All six evidence items and five assumptions are required')
    if handoff['dataVersion']!=dataset.dataVersion or handoff['contract']!=raw['data']['contract']:
        raise ValueError('Legacy handoff and dataset versions/contract disagree')
    return dataset


def convert_verified_legacy_bundle(project_root:Path,bundle:Path,out:Path):
    """Re-wrap a genuinely supplied signed legacy bundle; never create approval.

    Original reviewer, timestamp, version and source hashes remain unaltered.
    The derived receipt is an integrity wrapper, not a new human attestation.
    """
    dataset=verify_legacy_review_bundle(project_root,bundle)
    if out.exists(): raise FileExistsError('New output directory required')
    original=read_json_object(bundle/'review_receipt.json')
    raw=read_json_object(bundle/'dataset_success.json')
    scope={'kind':'CAUSORA_EVIDENCE_REVIEW_SCOPE_V1','schemaVersion':'causora.contract.v1',
        'dataVersion':dataset.dataVersion,'datasetSha256':sha256_json(raw),'sourceHashes':original['sourceHashes']}
    receipt={'kind':'CAUSORA_HUMAN_REVIEW_RECEIPT_V1','reviewerType':'human',
        'reviewerName':original['reviewerName'],'reviewedAtUtc':original['reviewedAtUtc'],
        'scopeSha256':sha256_json(scope),'datasetSha256':sha256_json(raw),
        'sourceHashes':original['sourceHashes'],'allApproved':True,
        'approvedEvidenceIds':original['approvedEvidenceIds'],'approvedAssumptionKeys':original['approvedAssumptionKeys']}
    ReviewScope.model_validate(scope); HumanReceipt.model_validate(receipt)
    provenance={'kind':'DERIVED_FROM_ORIGINAL_DAY2_VERIFIED_REVIEW_NOT_NEW_ATTESTATION',
        'dataVersionUnchanged':dataset.dataVersion,'originalReceipt':original,
        'originalManifestSha256':__import__('hashlib').sha256((bundle/'bundle_manifest.json').read_bytes()).hexdigest(),
        'warning':'Identity remains self-attested, not authenticated. No pending AI candidate may be substituted.'}
    out.mkdir(parents=True)
    for name,value in [('dataset_success.json',raw),('review_scope.json',scope),('human_receipt.json',receipt),('legacy_provenance.json',provenance)]:
        (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return provenance
