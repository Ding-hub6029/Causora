"""Single-worker public review admission; never charges or changes a simulation."""
import asyncio
import os
import time
from uuid import uuid4

from starlette.responses import JSONResponse


class ReviewAdmissionMiddleware:
    def __init__(self, app, *, enabled=None, cooldown=15.0, clock=time.monotonic):
        self.app = app
        self.enabled = enabled
        self.cooldown = cooldown
        self.clock = clock
        self.lock = asyncio.Lock()
        self.active = False
        self.last_started = float('-inf')

    async def __call__(self, scope, receive, send):
        enabled = self.enabled if self.enabled is not None else os.getenv('CAUSORA_PUBLIC_REVIEW_ADMISSION') == 'YES'
        if not enabled or scope['type'] != 'http' or scope['method'] != 'POST' or scope['path'] != '/api/boardroom':
            return await self.app(scope, receive, send)
        async with self.lock:
            remaining = self.cooldown - (self.clock() - self.last_started)
            reason = 'review_busy' if self.active else ('review_rate_limited' if remaining > 0 else None)
            if reason is None:
                self.active = True
                self.last_started = self.clock()
        if reason:
            request_id = 'req-' + uuid4().hex
            response = JSONResponse(status_code=429, content={
                'schemaVersion': 'causora.contract.v1', 'requestId': request_id,
                'error': {'code': 'validation_error', 'requestId': request_id,
                          'message': 'Another AI review is running. Retry after it finishes.' if reason == 'review_busy' else 'Please wait briefly before requesting another AI review.',
                          'details': {'reason': reason}}},
                headers={'Retry-After': str(max(1, int(remaining) + 1)), 'Cache-Control': 'no-store', 'X-Request-Id': request_id})
            return await response(scope, receive, send)
        try:
            await self.app(scope, receive, send)
        finally:
            async with self.lock:
                self.active = False
