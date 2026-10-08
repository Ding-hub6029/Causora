"""Temporary developer HTTP harness, NOT a team/production service or v1 substitute.

Only explicit --enable-unreviewed-dev enables /dev/*. POST /api/simulate delegates
unchanged to Jinzhu's formal boundary and remains 503 without verified review+MC.
"""
from __future__ import annotations
import asyncio
import importlib
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from .dev_bridge import _load_engine,build_development_bundle,verify_development_bundle
from .dev_roles import DevClaimStubProvider,run_dev_parallel


def make_server(root:Path,host='127.0.0.1',port=0,*,enabled:bool=False):
    if enabled is not True: raise PermissionError('Development server requires explicit enabled=True')
    root=root.resolve(); _load_engine(root)
    boundary=importlib.import_module('simulation_day2.api_boundary').simulate_v1_boundary

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass

        def reply(self,status,value):
            raw=json.dumps(value,ensure_ascii=False,allow_nan=False).encode('utf-8')
            self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
            self.end_headers(); self.wfile.write(raw)

        def do_GET(self):
            if self.path!='/dev/health': return self.reply(404,{'kind':'DEV_HARNESS_ERROR','code':'NOT_A_PRODUCTION_ENDPOINT'})
            self.reply(200,{'kind':'CAUSORA_UNREVIEWED_DEV_HARNESS_HEALTH','mode':'DEVELOPMENT_ONLY',
                'humanReviewStatus':'pending','decisionReady':False,'backend':'SUPPLIED_JINZHU_DETERMINISTIC_FUNCTION',
                'formalSimulateSuccessAvailable':False,'contractVersion':'causora.contract.v1'})

        def do_POST(self):
            if self.path not in {'/dev/compute','/dev/analyse','/api/simulate'}:
                return self.reply(404,{'kind':'DEV_HARNESS_ERROR','code':'NOT_A_PRODUCTION_ENDPOINT'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1_000_000 or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                    return self.reply(400,{'kind':'DEV_HARNESS_ERROR','code':'JSON_BODY_REQUIRED'})
                value=json.loads(self.rfile.read(size).decode('utf-8'))
                if not isinstance(value,dict): raise ValueError('Object required')
                if self.path=='/api/simulate':
                    status,response=boundary(value,request_id='req-dev-harness-formal-guard',project_root=root)
                    return self.reply(status,response)
                if set(value)-{'request','scenarioId'}: raise ValueError('Unknown development parameters')
                scenario=value.get('scenarioId','demand-drop')
                if scenario not in {'baseline','demand-drop','lead-stress'}: raise ValueError('Unknown scenario')
                bundle=build_development_bundle(root,enabled=True,request=value.get('request'))
                verify_development_bundle(bundle,root,enabled=True)
                if self.path=='/dev/compute': return self.reply(200,bundle)
                result=asyncio.run(run_dev_parallel(bundle,provider=DevClaimStubProvider(),enabled=True,scenario_id=scenario))
                self.reply(200,result)
            except Exception:
                # Exception text may contain server paths/source data; never echo it.
                self.reply(400,{'kind':'DEV_HARNESS_ERROR','code':'DEV_INPUT_OR_SOURCE_INVALID','decisionReady':False})

    return ThreadingHTTPServer((host,port),Handler)


def serve(root,host,port,*,enabled=False):
    server=make_server(root,host,port,enabled=enabled)
    print(f'UNREVIEWED DEVELOPMENT ONLY at http://{host}:{server.server_port}; formal success unavailable.',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
