# -*- coding: utf-8 -*-

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse


async def http_exception_handler(request: Request, e: HTTPException):
    return JSONResponse({'ok': False, 'message': e.detail}, status_code=e.status_code)


async def unhandled_exception_handler(request: Request, e: Exception):
    return JSONResponse({'ok': False, 'message': type(e).__name__ + ": " + str(e)}, status_code=500)


class App(Starlette):
    def __init__(self):
        super().__init__()
        self.debug = True
        self.add_exception_handler(HTTPException, http_exception_handler)
        self.add_exception_handler(Exception, unhandled_exception_handler)
