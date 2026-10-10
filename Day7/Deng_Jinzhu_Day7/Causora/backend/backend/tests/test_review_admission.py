import asyncio
from app.review_admission import ReviewAdmissionMiddleware


def test_busy_cooldown_and_release_without_provider_calls():
    async def exercise():
        entered, release = asyncio.Event(), asyncio.Event()
        calls = []
        now = [0.0]
        async def downstream(scope, receive, send):
            calls.append(scope['path'])
            if scope['path'] == '/api/boardroom':
                entered.set()
                await release.wait()
            await send({'type': 'http.response.start', 'status': 200, 'headers': []})
            await send({'type': 'http.response.body', 'body': b'ok'})
        middleware = ReviewAdmissionMiddleware(downstream, enabled=True, clock=lambda: now[0])
        async def invoke(path):
            messages = []
            async def receive(): return {'type': 'http.request', 'body': b''}
            async def send(message): messages.append(message)
            await middleware({'type': 'http', 'method': 'POST', 'path': path}, receive, send)
            return messages
        first = asyncio.create_task(invoke('/api/boardroom'))
        await entered.wait()
        busy = await invoke('/api/boardroom')
        assert busy[0]['status'] == 429 and b'review_busy' in busy[1]['body']
        assert (await invoke('/api/simulate'))[0]['status'] == 200
        release.set()
        assert (await first)[0]['status'] == 200
        limited = await invoke('/api/boardroom')
        assert limited[0]['status'] == 429 and b'review_rate_limited' in limited[1]['body']
        now[0] = 16.0
        assert (await invoke('/api/boardroom'))[0]['status'] == 200
        assert calls.count('/api/boardroom') == 2
    asyncio.run(exercise())


def test_failure_releases_slot():
    async def exercise():
        async def broken(*args): raise RuntimeError('fixture')
        middleware = ReviewAdmissionMiddleware(broken, enabled=True, cooldown=0)
        for _ in range(2):
            try:
                await middleware({'type': 'http', 'method': 'POST', 'path': '/api/boardroom'}, None, None)
            except RuntimeError:
                pass
            else:
                assert False
            assert middleware.active is False
    asyncio.run(exercise())


def test_public_throttle_keeps_cors_header():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient
    app = FastAPI()
    @app.post('/api/boardroom')
    def review(): return {'fixture': True}
    app.add_middleware(ReviewAdmissionMiddleware, enabled=True)
    app.add_middleware(CORSMiddleware, allow_origins=['https://causora-one.vercel.app'], allow_methods=['POST'])
    with TestClient(app) as client:
        headers={'Origin':'https://causora-one.vercel.app'}
        assert client.post('/api/boardroom',headers=headers).status_code == 200
        response=client.post('/api/boardroom',headers=headers)
        assert response.status_code == 429
        assert response.headers['access-control-allow-origin'] == headers['Origin']
        assert int(response.headers['retry-after']) >= 1
