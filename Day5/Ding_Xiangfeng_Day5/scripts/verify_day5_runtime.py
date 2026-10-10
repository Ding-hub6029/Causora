import json
import os
import urllib.request
import urllib.error
import time
from pathlib import Path
from datetime import datetime, timezone

root = Path(__file__).resolve().parents[1]
output = Path(os.getenv('CAUSORA_VERIFY_OUTPUT', str(root / '.runtime/day5-http-check')))
output.mkdir(parents=True, exist_ok=True)
golden = json.loads((root/'verification/g4-final/verified_golden_e2e.json').read_text(encoding='utf-8'))
base = os.getenv('CAUSORA_VERIFY_URL', 'http://127.0.0.1:3000').rstrip('/')
def call(path, body=None):
    request = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers={'Content-Type':'application/json'})
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    raw = response.read()
    return response.status, dict(response.headers), json.loads(raw)

if os.getenv('CAUSORA_VERIFY_KEYLESS_SERVER_CONFIRMED') != 'YES':
    raise SystemExit('Start an isolated server without provider credentials, then explicitly set CAUSORA_VERIFY_KEYLESS_SERVER_CONFIRMED=YES. This check must not run against a paid configured server.')

records = []
for index in range(10):
    start = time.monotonic()
    status, headers, response = call('/api/simulate', golden['simulationRequest'])
    assert status == 200 and headers.get('X-Causora-Review-Status', headers.get('x-causora-review-status')) == 'reviewed'
    actual = response['data']
    for field in ['matrix', 'deltas', 'selections']:
        left = actual['simulation'][field] if field == 'matrix' else actual[field]
        right = golden['simulationResponse']['data']['simulation'][field] if field == 'matrix' else golden['simulationResponse']['data'][field]
        assert left == right, field
    request = {'schemaVersion':'causora.contract.v1','simulationId':actual['simulation']['simulationId'], 'dataVersion':response['dataVersion'], 'scenarioId':'baseline'}
    boardroom_status, _, unavailable = call('/api/boardroom', request)
    assert boardroom_status == 503 and unavailable['schemaVersion'] == 'causora.contract.v1'
    records.append({'index':index+1, 'requestId':response['requestId'], 'simulationId':actual['simulation']['simulationId'], 'simulationStatus':status, 'aiFailureStatus':boardroom_status, 'matrixEqualsVerifiedGolden':True, 'seconds':round(time.monotonic()-start,3)})
    if index == 0:
        (output/'current-live-simulation.json').write_text(json.dumps(response,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
evidence = []
for identity in ['EV-014','EV-019','EV-020','EV-021','EV-024','EV-027']:
    status, _, response = call('/api/evidence/'+identity)
    assert status == 200
    record = response['data'].get('evidence', response['data'])
    assert record['quoteMatched'] is True
    evidence.append({'id':identity,'status':status,'quoteMatched':True})
report = {'status':'PASS','recordedAtUtc':datetime.now(timezone.utc).isoformat(),'scope':'LOCAL_REVIEWED_SIMULATION_AND_AI_UNAVAILABLE_FALLBACK; NOT_NEW_PAID_MODEL_VALIDATION_OR_HUMAN_TEST','runs':records,'evidence':evidence}
(output/'runtime-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':'PASS','consecutiveSimulationAndFailurePaths':len(records),'evidence':len(evidence)}))

