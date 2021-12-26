from typing import List, Optional

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from .exceptions import (
    InvalidGametype,
    MatchAlreadyExists,
    MatchNotFound,
    PlayerNotFound,
)


# https://github.com/encode/starlette/issues/433
def fixed_url_path_for(self, name: str, **path_params: str):
    path_params = {k: v for k, v in path_params.items() if v is not None}
    return self.bugged_url_path_for(name, **path_params)


Route.bugged_url_path_for = Route.url_path_for
Route.url_path_for = fixed_url_path_for


async def http_exception_handler(request: Request, e: HTTPException):
    from traceback import print_exc

    print_exc()
    context = {"message": e.detail}
    if request.url.path.lower().endswith(".json"):
        return JSONResponse(context, status_code=e.status_code)

    return PlainTextResponse(context["message"], status_code=e.status_code)


async def unhandled_exception_handler(request: Request, e: Exception):
    new_exc = HTTPException(500, type(e).__name__ + ": " + str(e))
    return await http_exception_handler(request, new_exc)


async def match_already_exists_exception_handler(
    request: Request, e: MatchAlreadyExists
):
    new_exc = HTTPException(409, "Match already exists: {}".format(e))
    return await http_exception_handler(request, new_exc)


async def invalid_gametype_exception_handler(request: Request, e: InvalidGametype):
    new_exc = HTTPException(442, "Invalid gametype: {}".format(e))
    return await http_exception_handler(request, new_exc)


async def match_not_found_exception_handler(request: Request, e: MatchNotFound):
    new_exc = HTTPException(404, "Match not found: {}".format(e))
    return await http_exception_handler(request, new_exc)


async def player_not_found_exception_handler(request: Request, e: PlayerNotFound):
    new_exc = HTTPException(404, "Player not found: {}".format(e))
    return await http_exception_handler(request, new_exc)


class App(Starlette):
    def __init__(self, debug: bool = False, routes: Optional[List] = []):
        super().__init__(debug, routes)
        self.add_exception_handler(HTTPException, http_exception_handler)
        self.add_exception_handler(
            MatchAlreadyExists, match_already_exists_exception_handler
        )
        self.add_exception_handler(MatchNotFound, match_not_found_exception_handler)
        self.add_exception_handler(PlayerNotFound, player_not_found_exception_handler)
        self.add_exception_handler(Exception, unhandled_exception_handler)
