"""Explicit unreviewed v1-request/v2-response Monte Carlo role integration CLI."""
from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
from .mc_client import post_simulation,save_capture,load_capture
from .mc_roles import DevClaimStubProvider,run_mc_parallel


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(value,path):
    if path.exists(): raise FileExistsError('New output file required')
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


async def analyse(capture,scenario,provider_name,model,timeout):
    if provider_name=='offline': provider=DevClaimStubProvider()
    else:
        from .provider import SandboxProxyProvider
        provider=SandboxProxyProvider(model)
        catalog=await provider.client.models.list()
        item=next((m.model_dump() for m in catalog.data if m.id==model),None)
        if not item or not item.get('capabilities',{}).get('supports_response_format_json_schema'):
            await provider.client.close()
            raise ValueError('Live model catalog does not confirm strict structured output support')
    try:
        return await run_mc_parallel(capture['request'],capture['response'],provider=provider,
            scenario_id=scenario,enabled=True,headers=capture['transport']['headers'],timeout_seconds=timeout)
    finally:
        if provider_name!='offline': await provider.client.close()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['fetch','analyse','fetch-analyse','review-draft','verify-review-native'])
    parser.add_argument('--enable-unreviewed-dev',action='store_true')
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--request',type=Path);parser.add_argument('--capture',type=Path)
    parser.add_argument('--out',type=Path);parser.add_argument('--scenario',choices=['baseline','demand-drop','lead-stress'],default='baseline')
    parser.add_argument('--provider',choices=['offline','model'],default='offline');parser.add_argument('--model',default='gpt-5-mini')
    parser.add_argument('--timeout-seconds',type=float,default=45)
    parser.add_argument('--http-timeout-seconds',type=float,default=180)
    parser.add_argument('--backend-root',type=Path);parser.add_argument('--review-bundle',type=Path)
    args=parser.parse_args(argv)
    if args.action=='verify-review-native':
        if not args.backend_root or not args.review_bundle: parser.error('--backend-root and --review-bundle required')
        from .mc_review_compat import verify_latest_review_bundle
        checked=verify_latest_review_bundle(args.backend_root,args.review_bundle)
        print(json.dumps({'kind':'NATIVE_REVIEW_FORMAT_VERIFIED_NOT_A_DECISION','dataVersion':checked['dataVersion'],
            'reviewReference':checked['reviewReference'],'contractPayloadSha256':checked['contractPayloadSha256']},indent=2));return
    if not args.enable_unreviewed_dev: parser.error('Explicit --enable-unreviewed-dev required; formal review is never disabled')
    if args.out is None: parser.error('--out is required')
    if args.action=='review-draft':
        if not args.backend_root: parser.error('--backend-root required')
        from .mc_review_compat import prepare_pending_native_review
        root=Path(__file__).resolve().parents[1]
        prepare_pending_native_review(root/'evidence_review/data/reviewed_data.json',root/'evidence_review/data/human_review_request.json',args.backend_root,args.out)
        print('PENDING native-format worksheet; no human approval or official reviewed filenames created.');return
    if args.action in {'fetch','fetch-analyse'}:
        if not args.request: parser.error('--request required for a fresh service call')
        capture=post_simulation(args.base_url,read(args.request),enabled=True,timeout_seconds=args.http_timeout_seconds)
        if args.action=='fetch': print(save_capture(capture,args.out));return
        if not args.capture: parser.error('--capture NEW_DIRECTORY required to retain the fresh HTTP evidence')
        save_capture(capture,args.capture)
    else:
        if not args.capture: parser.error('--capture required; raw response or mock cannot substitute for an immutable request/result record')
        capture=load_capture(args.capture)
    result=asyncio.run(analyse(capture,args.scenario,args.provider,args.model,args.timeout_seconds))
    write(result,args.out)
    print(args.out.resolve())
    print(result['state'],'UNREVIEWED MC DEVELOPMENT ONLY; no recommendation/approval; decisionReady=false.')

if __name__=='__main__': main()
