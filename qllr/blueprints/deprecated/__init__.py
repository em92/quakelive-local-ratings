# -*- coding: utf-8 -*-

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse

from qllr.app import App
from qllr.endpoints import Endpoint

from .methods import get_player_info_old

bp = App()


@bp.route("/player/{steam_id:int}.json")
class DeprecatedPlayerJson(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        steam_id = request.path_params["steam_id"]
        return JSONResponse(await get_player_info_old(con, steam_id))
