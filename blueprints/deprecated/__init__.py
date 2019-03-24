# -*- coding: utf-8 -*-

from app import App
from starlette.responses import JSONResponse
from starlette.requests import Request
from endpoints import Endpoint
from .methods import get_player_info_old
from asyncpg import Connection

bp = App()


@bp.route("/player/{steam_id:int}.json")
class DeprecatedPlayerJson(Endpoint):
    async def _get(self, request: Request, con: Connection):
        steam_id = request.path_params['steam_id']
        return JSONResponse(await get_player_info_old(con, steam_id))
