"""AI-assisted synthetic review only. Never signs a human receipt or simulates KPIs."""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pymupdf

from causora_day1.evidence import extract_baseline, verify_source

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_IDS = ('EV-014', 'EV-019', 'EV-021', 'EV-024', 'EV-027', 'EV-020')
ASSUMPTIONS = ('decisionDate', 'renewalDate', 'noticeSent', 'forecastBasis', 'lockedForecastUnits24m')
DISPLAY = {'EV-014': '60 days', 'EV-019': '24 months', 'EV-021': '14%',
           'EV-024': '60%', 'EV-027': '$25,000', 'EV-020': 'conditional auto-renew clause present'}
ALIASES = {'EV-014': 'renewal_notice_days', 'EV-024': 'minPurchaseShareA'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def check_sources(root: Path):
    pins = load(root / 'reference/source_hashes.json')
    for name, expected in pins.items():
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen source changed: ' + name)
    return pins


def derive(contract: dict):
    decision = date.fromisoformat(contract['decisionDate'])
    renewal = date.fromisoformat(contract['renewalDate'])
    deadline = renewal - timedelta(days=contract['renewalNoticeDays'])
    return {'daysToRenewal': (renewal - decision).days,
            'noticeDeadline': deadline.isoformat(),
            'renewalLocked': decision > deadline and not contract['noticeSent'],
            'minPurchaseUnitsA': round(contract['lockedForecastUnits24m'] * contract['minPurchaseShareA'])}


def normalized_finding_value(finding, ident):
    value = json.loads(finding['valueJson'])
    if isinstance(value, dict):
        # A few review workers returned ancillary fields. Extract ONLY this item's
        # named value, compare its exact type/value below, and record normalization.
        key = ALIASES.get(ident, ident)
        if key not in value:
            raise ValueError('Reviewer did not return the requested single value: ' + ident)
        return value[key], True
    return value, False


def build(root: Path = ROOT, findings: dict | None = None):
    pins = check_sources(root)
    mock = load(root / 'fixtures/causora_day1_mock.json')
    c = mock['contract']
    if mock['meta']['status'] != 'verified-local-mock':
        raise ValueError('Input must remain explicitly LOCAL MOCK')
    summary = extract_baseline(root / 'fixtures/demo/supplier_a_agreement.pdf', root / 'fixtures/causora_day1_mock.json')
    verify_source(summary, root / 'fixtures/demo/supplier_a_agreement.pdf')
    if {r.id for r in summary.records} != set(EVIDENCE_IDS):
        raise ValueError('Six evidence records required')
    if any(not r.quote_matched or r.manually_verified or r.page != 4 for r in summary.records):
        raise ValueError('All six must match; manual verification must remain false')
    derived = derive(c)
    if any(c[key] != value for key, value in derived.items()):
        raise ValueError('Configured dates or minimum do not match derived inputs')
    with (root / 'fixtures/demo/supplier_correspondence_log.csv').open(encoding='utf-8', newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows or any(r['provenance'] != 'synthetic_mock_not_a_real_supplier_record' or
                       r['valid_written_nonrenewal_notice'] not in ('true', 'false') for r in rows):
        raise ValueError('Notice register is not a valid explicitly synthetic register')
    timely = any(r['valid_written_nonrenewal_notice'] == 'true' and
                 date.fromisoformat(r['date']) <= date.fromisoformat(c['noticeDeadline']) for r in rows)
    if timely is not c['noticeSent']:
        raise ValueError('Notice assumption disagrees with synthetic register')
    with pymupdf.open(root / 'fixtures/demo/supplier_a_agreement.pdf') as doc:
        page = doc[3].get_text()
    if 'forecast is fixed at 26,000 units' not in page or c['forecastBasis'] != 'locked-at-renewal':
        raise ValueError('Locked forecast assumption lacks the given synthetic source')
    findings = findings if findings is not None else load(root / 'reference/review_findings_raw.json')
    if findings.get('failures'):
        raise ValueError('Review workers failed; preserve pending, do not build completed review')
    by_id = {item['id']: item for item in findings['items']}
    if len(by_id) != 11 or set(by_id) != set(EVIDENCE_IDS + ASSUMPTIONS):
        raise ValueError('Review must contain exactly eleven unique item IDs')
    ledger = []
    for ident in EVIDENCE_IDS + ASSUMPTIONS:
        finding = by_id[ident]
        expected = DISPLAY[ident] if ident in EVIDENCE_IDS else c[ident]
        value, normalized = normalized_finding_value(finding, ident)
        decision = finding['syntheticDecision']
        reason = finding['reason']
        if type(value) is not type(expected) or value != expected:
            decision = 'pending'
            reason = 'Review value/type disagrees with the frozen single-item value; owner clarification required.'
        ledger.append({'id': ident, 'group': 'evidence' if ident in EVIDENCE_IDS else 'assumption',
            'value': expected, 'syntheticDecision': decision, 'reviewerType': 'AI_ASSISTED',
            'humanDecision': 'pending', 'realWorldVerification': 'not_verified',
            'source': finding['source'], 'reason': reason,
            'normalizationNote': 'Ancillary worker fields removed; only the scoped item was type/value checked.' if normalized else None,
            'pendingReason': 'The PDF requires a separate human field review; no human attestation was provided. Real supplier facts are outside this synthetic review.',
            'limitations': finding['limitations']})
    scope = {'sourceHashes': pins, 'contract': c,
             'records': summary.model_dump(mode='json')['records'], 'items': ledger}
    scope_hash = digest(scope)
    candidate_version = mock['meta']['dataVersion'] + '-wang-ai-review-' + scope_hash[:12]
    wire_evidence = []
    records = {r.id: r for r in summary.records}
    for old in mock['evidence']:
        entry = copy.deepcopy(old)
        entry['locatorBbox'] = records[entry['id']].locator_bbox
        wire_evidence.append(entry)
    candidate = {'kind': 'CAUSORA_AI_REVIEWED_SYNTHETIC_INPUT_CANDIDATE',
        'schemaVersion': 'causora.contract.v1', 'dataVersion': candidate_version,
        'baselineDataVersion': mock['meta']['dataVersion'], 'datasetId': 'ds-001',
        'sourceMode': 'LOCAL_MOCK', 'permittedUse': 'SYNTHETIC_DEVELOPMENT_ONLY',
        'humanReviewStatus': 'pending', 'realWorldVerificationStatus': 'not_verified',
        'simulationState': 'NOT_COMPUTED', 'decisionReady': False,
        'scopeSha256': scope_hash, 'sourceHashes': pins,
        'contract': copy.deepcopy(c), 'evidence': wire_evidence,
        'variables': copy.deepcopy(mock['variables']),
        'conditionalAutoRenewEvidenceId': 'EV-020',
        'integrationNote': 'Internal candidate, NOT DatasetResult/ApiSuccess. Do not publish ready or LIVE. EV-020 remains internal; do not add it to the five public evidence IDs without team approval.'}
    human = {'kind': 'CAUSORA_SYNTHETIC_HUMAN_REVIEW_REQUEST', 'scopeSha256': scope_hash,
        'reviewerType': 'human', 'reviewerName': '', 'reviewedAtUtc': '',
        'sourceHashes': pins, 'evidence': [], 'assumptions': []}
    for item in ledger:
        dest = human['evidence' if item['group'] == 'evidence' else 'assumptions']
        dest.append({'id': item['id'], 'expectedValue': item['value'], 'decision': 'pending',
                     'confirmedValue': None, 'notes': item['pendingReason']})
    review = {'kind': 'CAUSORA_AI_SYNTHETIC_REVIEW_LEDGER', 'scopeSha256': scope_hash,
        'sourceMode': 'LOCAL_MOCK', 'reviewerType': 'AI_ASSISTED',
        'humanReviewStatus': 'pending', 'realWorldVerificationStatus': 'not_verified',
        'decisionReady': False, 'items': ledger,
        'publicEvidencePolicy': 'Five unchanged public IDs; EV-020 retained internally as conditional clause, not a sixth public DTO.',
        'sourceHashes': pins, 'derivations': derived}
    return {'reviewed_data.json': candidate, 'review_ledger.json': review,
            'evidence_summary.json': summary.model_dump(mode='json'), 'human_review_request.json': human}


def write_outputs(out: Path, outputs):
    out.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (out / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Reproduce AI-assisted synthetic review; human status stays pending')
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--out', type=Path, required=True, help='New output directory; existing outputs are not overwritten')
    args = parser.parse_args()
    if args.out.exists() and any(args.out.iterdir()):
        raise FileExistsError('Use a fresh directory to avoid overwriting review audit records')
    write_outputs(args.out, build(args.root.resolve()))
    print('Synthetic review data emitted; no human signature, simulation or approval produced.')


if __name__ == '__main__':
    main()
