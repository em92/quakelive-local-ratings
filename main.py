#!/usr/bin/env python3

import uvicorn
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from qllr import app
from qllr.settings import HOST, PORT, TRUSTED_PROXIES


class TrustedProxiesMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if "x-forwarded-for" in request.headers:
            if request.client.host not in TRUSTED_PROXIES:
                return PlainTextResponse("Client address spoofing detected", 403)
        return await call_next(request)


if TRUSTED_PROXIES:
    app.add_middleware(ProxyHeadersMiddleware)
    app.add_middleware(TrustedProxiesMiddleware)

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, lifespan="on")
