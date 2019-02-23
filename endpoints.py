# -*- coding: utf-8 -*-

from email.utils import parsedate

from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send

class Endpoint(HTTPEndpoint):
    '''
    def is_not_modified(self, stat_headers: typing.Dict[str, str]) -> bool:
        etag = stat_headers["etag"]
        last_modified = stat_headers["last-modified"]
        req_headers = Headers(scope=self.scope)
        if etag == req_headers.get("if-none-match"):
            return True
        if "if-modified-since" not in req_headers:
            return False
        last_req_time = req_headers["if-modified-since"]

        return parsedate(last_req_time) >= parsedate(last_modified)  # type: ignore
    '''

    async def __call__(self, receive: Receive, send: Send) -> None:
        request = Request(self.scope, receive=receive)
        response = await self.dispatch(request)
        await response(receive, send)
