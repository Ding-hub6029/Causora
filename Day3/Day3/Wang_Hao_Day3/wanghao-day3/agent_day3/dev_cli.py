"""English CLI for explicit unreviewed development; never a production API replacement."""
from __future__ import annotations
import argparse
import asyncio
import json
from pathlib import Path
from .dev_bridge import build_development_bundle,verify_development_bundle,write_development_bundle
from .wire_models import read_json_object


async def analyse(bundle,provider_name,model,scenario,timeout):
    from .dev_roles import DevClaimStubProvider,run_dev_parallel
    if provider_name=='offline': provider=DevClaimStubProvider()
    else:
        from .provider import SandboxProxyProvider
        provider=SandboxProxyProvider(model)
        catalog=await provider.client.models.list()
        entry=next((m.model_dump() for m in catalog.data if m.id==model),None)
        if not entry or not entry.get('capabilities',{}).get('supports_response_format_json_schema'):
            await provider.client.close()
            raise ValueError('Current model catalog does not confirm strict JSON-schema support')
    try: return await run_dev_parallel(bundle,provider=provider,enabled=True,scenario_id=scenario,timeout_seconds=timeout)
    finally:
        if provider_name!='offline': await provider.client.close()


def write(value,out):
    if out.exists(): raise FileExistsError('New analysis output required')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['compute','analyse','serve','convert-verified-review'])
    parser.add_argument('--jinzhu-root',type=Path,required=True,help='Combined source root made by bootstrap_dev_workspace.py')
    parser.add_argument('--enable-unreviewed-dev',action='store_true',help='Separate development configuration; cannot enable any formal success path')
    parser.add_argument('--out',type=Path); parser.add_argument('--bundle',type=Path)
    parser.add_argument('--request',type=Path); parser.add_argument('--policy',type=Path)
    parser.add_argument('--provider',choices=['offline','model'],default='offline')
    parser.add_argument('--model',default='gpt-5-mini')
    parser.add_argument('--scenario',choices=['baseline','demand-drop','lead-stress'],default='demand-drop')
    parser.add_argument('--timeout-seconds',type=float,default=45)
    parser.add_argument('--host',default='127.0.0.1'); parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args(argv)
    if args.action=='convert-verified-review':
        if not args.bundle or not args.out: parser.error('conversion requires --bundle and --out')
        from .review_compat import convert_verified_legacy_bundle
        convert_verified_legacy_bundle(args.jinzhu_root,args.bundle,args.out)
        print('Existing verified review wrapped; no approval or signature created.'); return
    if not args.enable_unreviewed_dev: parser.error('This path requires --enable-unreviewed-dev; formal review remains enforced')
    if args.action=='serve':
        if args.provider!='offline': parser.error('HTTP harness deliberately uses the offline code-bound selector; run model smoke explicitly via analyse')
        from .dev_http import serve
        serve(args.jinzhu_root,args.host,args.port,enabled=True); return
    if args.out is None: parser.error('--out is required')
    if args.bundle:
        if args.action=='compute': parser.error('compute cannot reuse a saved bundle')
        bundle=read_json_object(args.bundle)
    else:
        bundle=build_development_bundle(args.jinzhu_root,enabled=True,
            request=read_json_object(args.request) if args.request else None,
            policy=read_json_object(args.policy) if args.policy else None)
    verify_development_bundle(bundle,args.jinzhu_root,enabled=True)
    if args.action=='compute': write_development_bundle(bundle,args.out)
    else: write(asyncio.run(analyse(bundle,args.provider,args.model,args.scenario,args.timeout_seconds)),args.out)
    print(str(args.out.resolve()))
    print('UNREVIEWED DEVELOPMENT ONLY; synthetic inputs, actual deterministic calculation, no MC probability/P90 or recommendation.')

if __name__=='__main__': main()
