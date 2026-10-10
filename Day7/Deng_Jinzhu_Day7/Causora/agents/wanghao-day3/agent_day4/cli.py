"""Owner CLI for current-run capture and explicitly non-formal developer smoke."""
from __future__ import annotations
import argparse,asyncio,json,sys
from pathlib import Path
from uuid import uuid4
from .inputs import make_verified_run,validate_run
from .provider import providers_from_env
from .pipeline import run_boardroom,run_development_analysis
from .wire import PipelineError,PipelineConfig


def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def write_json(path,value):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def run_from_capture(capture,source_root):
    root=Path(source_root).resolve();dataset=read_json(root/'demo_data/causora_day1_mock.json')
    response=capture['response'];context=response['data']['executionContext']
    if context['mode']=='reviewed_release_gated':
        bundle=read_json(root/'reviewed/wang-2026-10-07/reviewed_contract.json');contract=bundle
    else:contract=dataset['contract']
    evidence=dataset['evidence']
    # EV-020 is already the reviewed native conditional-source ID. This adapter
    # materializes its existing source clause rather than inventing another ID.
    renewal=next(e for e in evidence if e['id']=='EV-019')
    evidence=[*evidence,{**renewal,'id':'EV-020','extractedField':'auto_renew','extractedValue':True,'locatorBbox':None}]
    run=make_verified_run(simulation_request=capture['request'],simulation_response=response,contract=contract,evidence=evidence,
        source_root=root,simulation_request_id=capture.get('simulationRequestId',response['requestId']))
    return validate_run(run,require_reviewed=context['mode']=='reviewed_release_gated')


async def analyse_capture(args):
    run=run_from_capture(read_json(args.capture),args.source_root)
    if not run.reviewed and not args.enable_unreviewed_dev:raise ValueError('Explicit --enable-unreviewed-dev is required; formal transport is blocked')
    simulation=run.simulation_response['data']['simulation']
    request={'schemaVersion':'causora.contract.v1','simulationId':simulation['simulationId'],'dataVersion':simulation['dataVersion'],'scenarioId':args.scenario}
    if run.simulation_response['data']['selections'][args.scenario]['status']=='no_feasible_option':
        primary=critic=fallback=None;config=PipelineConfig()
    else:primary,critic,fallback,config=providers_from_env()
    try:
        fn=run_boardroom if run.reviewed else run_development_analysis
        output=await fn(request,run=run,provider=primary,critic_provider=critic,fallback_provider=fallback,
            correlation_id='br-'+uuid4().hex,config=config)
        if run.reviewed:output={'envelope':output.envelope,'headers':output.headers,'audit':output.audit}
        write_json(args.output,output)
    finally:
        for instance in {id(p):p for p in (primary,critic,fallback)}.values():
            close=getattr(instance,'aclose',None)
            if close:await close()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Causora Wang Day4 current-run tools; no implicit replay or approval')
    sub=parser.add_subparsers(dest='command',required=True)
    fetch=sub.add_parser('capture-simulation',help='Request the existing backend once and save the current response')
    fetch.add_argument('--url',default='http://127.0.0.1:8000');fetch.add_argument('--request',required=True);fetch.add_argument('--output',required=True)
    analyse=sub.add_parser('analyse-current',help='Consume a saved current result; never rerun Monte Carlo')
    analyse.add_argument('--capture',required=True);analyse.add_argument('--source-root',required=True);analyse.add_argument('--scenario',choices=['baseline','demand-drop','lead-stress'],default='demand-drop')
    analyse.add_argument('--enable-unreviewed-dev',action='store_true');analyse.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    try:
        if args.command=='capture-simulation':
            import httpx
            request=read_json(args.request);request_id='sim-'+uuid4().hex
            response=httpx.post(args.url.rstrip('/')+'/api/simulate',json=request,headers={'X-Request-Id':request_id},timeout=120)
            response.raise_for_status();payload=response.json()
            if payload.get('requestId')!=request_id:raise ValueError('Simulation transport correlation mismatch')
            write_json(args.output,{'request':request,'response':payload,'simulationRequestId':request_id,
                'headers':{key:response.headers[key] for key in ('x-request-id','x-causora-review-status','x-causora-execution-mode','x-causora-trace-contract') if key in response.headers},
                'captureKind':'ACTUAL_BACKEND_HTTP_RESPONSE'})
        else:asyncio.run(analyse_capture(args))
    except PipelineError as exc:
        print(json.dumps({'status':'failed','reason':exc.reason,'retryable':exc.retryable}),file=sys.stderr);return 1
    except Exception:
        print('Operation failed; no simulation or approval state was changed.',file=sys.stderr);return 1
    return 0

if __name__=='__main__':raise SystemExit(main())
