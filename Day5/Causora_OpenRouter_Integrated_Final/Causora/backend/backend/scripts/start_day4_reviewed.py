"""Start the approved synthetic Day 4 service with all independent gates intact."""
import argparse
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parents[1]

def configure():
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    os.environ.pop('CAUSORA_DEV_UNREVIEWED_MODE', None)
    values = {
        'CAUSORA_REVIEW_BUNDLE_DIR': BACKEND / 'reviewed/wang-2026-10-07',
        'CAUSORA_APPROVED_POLICY_PATH': PROJECT / 'release/model_policy.APPROVED.json',
        'CAUSORA_POLICY_APPROVAL_RECORD_PATH': PROJECT / 'release/policy_approval.APPROVED.json',
        'CAUSORA_TRACE_CONTRACT_V2_RELEASE_RECORD': PROJECT / 'release/trace_release.RELEASED.json',
        'CAUSORA_COMMON_API_CONTRACT_PATH': PROJECT / 'API_CONTRACT_V2.md',
        'CAUSORA_TYPESCRIPT_V2_TYPES_PATH': PROJECT / 'frontend/lib/contracts-v2.ts',
        'CAUSORA_FRONTEND_V2_VALIDATOR_PATH': PROJECT / 'frontend/lib/simulate-api.ts',
    }
    for key, path in values.items():
        if not path.exists(): raise SystemExit('Required release artifact missing: ' + str(path))
        os.environ[key] = str(path)
    os.environ['CAUSORA_REVIEW_VERIFIER'] = 'app.release_verifiers:verify_reviewed_bundle_record'
    os.environ['CAUSORA_POLICY_VERIFIER'] = 'app.release_verifiers:verify_team_policy_record'
    os.environ['CAUSORA_TRACE_CONTRACT_V2_VERIFIER'] = 'app.release_verifiers:verify_trace_contract_release'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535: parser.error('port must be 1..65535')
    configure()
    import uvicorn
    uvicorn.run('app.service:app', host='127.0.0.1', port=args.port)

if __name__ == '__main__': main()
