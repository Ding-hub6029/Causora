"""Explicit developer client for Jinzhu's v1-request / v2-response MC service.

No cache, fixture fallback, approval creation, engine import, or frontend mutation.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
import urllib.error
import urllib.request
from uuid import uuid4


def _sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()


def _finite(value):
    if isinstance(value,float):
        import math
        if not math.isfinite(value): raise ValueError('Non-finite JSON value')
    elif isinstance(value,dict):
        for child in value.values(): _finite(child)
    elif isinstance(value,list):
        for child in value: _finite(child)


def _validate_url(base_url):
    value=urlsplit(base_url)
    if value.scheme not in {'http','https'} or not value.hostname or value.username or value.password or value.query or value.fragment:
        raise ValueError('A server base URL without credentials/query/fragment is required')
    return base_url.rstrip('/')+'/api/simulate'


def post_simulation(base_url:str,request:dict,*,enabled:bool=False,timeout_seconds:float=180,validate:bool=True):
    if enabled is not True: raise PermissionError('Monte Carlo development requires explicit enabled=True')
    if not isinstance(request,dict) or request.get('schemaVersion')!='causora.contract.v1': raise ValueError('Exact v1 request required')
    _finite(request)
    if isinstance(timeout_seconds,bool) or not 0<timeout_seconds<=600: raise ValueError('HTTP timeout must be between zero and 600 seconds')
    request_id='req-wang-mc-'+uuid4().hex
    body=json.dumps(request,ensure_ascii=False,allow_nan=False).encode('utf-8')
    req=urllib.request.Request(_validate_url(base_url),data=body,headers={
        'Content-Type':'application/json','Accept':'application/json','X-Request-Id':request_id},method='POST')
    try:
        with urllib.request.urlopen(req,timeout=timeout_seconds) as response:
            status=response.status; headers={k.lower():v for k,v in response.headers.items()}
            raw=response.read(20_000_001)
    except urllib.error.HTTPError as exc:
        # Keep typed failure local, never fabricate a simulation or silently use a fixture.
        payload=json.loads(exc.read().decode('utf-8'))
        reason=payload.get('error',{}).get('details',{}).get('reason','http_error')
        raise ValueError(f'Simulation service HTTP {exc.code}; reason={reason}') from None
    if status!=200 or len(raw)>20_000_000: raise ValueError('Invalid/oversized service response')
    value=json.loads(raw.decode('utf-8')); _finite(value)
    if value.get('requestId')!=request_id or headers.get('x-request-id')!=request_id: raise ValueError('Response does not bind this new HTTP request')
    if value.get('schemaVersion')!='causora.contract.v2': raise ValueError('Expected v2 success; v1 fixture/preview is not accepted')
    if validate:
        from .mc_validation import validate_mc_response
        audit=validate_mc_response(request,value,headers=headers)
    else:
        audit=None # Capture stage only; no role calls can use an unvalidated result.
    transport={'kind':'WANG_REAL_HTTP_MC_CAPTURE_V1','source':'LIVE_HTTP_REQUEST_TO_SUPPLIED_JINZHU_DAY3_SERVICE',
        'endpoint':_validate_url(base_url),'fetchedAtUtc':datetime.now(timezone.utc).isoformat(),
        'httpStatus':status,'requestId':request_id,'headers':headers,
        'requestSha256':_sha(request),'responseSha256':_sha(value),
        'validationStatus':'VALIDATED' if audit is not None else 'RAW_CAPTURE_NOT_YET_VALIDATED',
        'decisionReady':False}
    return {'request':request,'response':value,'transport':transport,'audit':audit}


def save_capture(capture:dict,directory:Path):
    if directory.exists(): raise FileExistsError('A new capture directory is required; do not replace an immutable run')
    directory.mkdir(parents=True)
    for name in ('request','response','transport','audit'):
        if capture.get(name) is not None:
            (directory/(name+'.json')).write_text(json.dumps(capture[name],ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return directory.resolve()


def load_capture(directory:Path):
    from .mc_validation import validate_mc_response
    value={key:json.loads((directory/(key+'.json')).read_text(encoding='utf-8')) for key in ('request','response','transport')}
    transport=value['transport']
    if transport.get('source')!='LIVE_HTTP_REQUEST_TO_SUPPLIED_JINZHU_DAY3_SERVICE' or transport.get('decisionReady') is not False:
        raise ValueError('Not an explicit live-HTTP development capture')
    if transport.get('validationStatus')!='VALIDATED' or transport.get('httpStatus')!=200: raise ValueError('Capture was not validated')
    if transport.get('requestSha256')!=_sha(value['request']) or transport.get('responseSha256')!=_sha(value['response']):
        raise ValueError('Capture input or result was replaced')
    if transport.get('requestId')!=value['response'].get('requestId'): raise ValueError('Wrong capture request identity')
    value['audit']=validate_mc_response(value['request'],value['response'],headers=transport['headers'])
    stored=json.loads((directory/'audit.json').read_text(encoding='utf-8'))
    if stored!=value['audit']: raise ValueError('Capture audit differs from current input/result')
    return value
