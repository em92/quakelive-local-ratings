# -*- coding: utf-8 -*-

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from exceptions import (
    InvalidGametype,
    MatchAlreadyExists
)


async def http_exception_handler(request: Request, e: HTTPException):
    return JSONResponse({'ok': False, 'message': e.detail}, status_code=e.status_code)


async def unhandled_exception_handler(request: Request, e: Exception):
    return JSONResponse({'ok': False, 'message': type(e).__name__ + ": " + str(e)}, status_code=500)


async def match_already_exists_exception_handler(request: Request, e: MatchAlreadyExists):
    new_exc = HTTPException(409, "Match already exists")
    return await http_exception_handler(request, new_exc)


async def invalid_gametype_exception_handler(request: Request, e: InvalidGametype):
    new_exc = HTTPException(442, "Invalid gametype: {}".format(e))
    return await http_exception_handler(request, new_exc)


class App(Starlette):
    def __init__(self, debug: bool = False, template_directory: str = None):
        super().__init__(debug, template_directory)
        self.add_exception_handler(HTTPException, http_exception_handler)
        self.add_exception_handler(MatchAlreadyExists, match_already_exists_exception_handler)
        self.add_exception_handler(Exception, unhandled_exception_handler)
