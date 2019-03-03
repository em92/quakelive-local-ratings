# -*- coding: utf-8 -*-

from time import gmtime
from email.utils import parsedate
from db import cache

from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send


class Endpoint(HTTPEndpoint):
    last_req_time = None

    def fast_response_if_not_modified(self, request: Request):
        if "if-modified-since" not in request.headers:
            return

        last_req_time = parsedate(request.headers["if-modified-since"])
        if last_req_time is None:
            return
        self.last_req_time = last_req_time

        if 'gametype' in request.path_params:
            # TODO: keyerror handling
            last_modified = cache.LAST_GAME_TIMESTAMPS[request.path_params["gametype"]]
        else:
            last_modified = max(cache.LAST_GAME_TIMESTAMPS.values())

        last_modified = gmtime(last_modified)[:]

        if last_req_time >= last_modified:
            raise HTTPException(304)

    async def __call__(self, receive: Receive, send: Send) -> None:
        request = Request(self.scope, receive=receive)
        self.fast_response_if_not_modified(request)
        response = await self.dispatch(request)
        await response(receive, send)
