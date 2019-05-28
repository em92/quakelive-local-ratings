# -*- coding: utf-8 -*-

from typing import Optional

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from qllr.app import App
from qllr.endpoints import Endpoint

from .methods import fetch, with_player_info_from_qlstats

bp = App()
bp.json_only_mode = True


@bp.route("/{ids:steam_ids}")
class BalanceSimple(Endpoint):
    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        ids = request.path_params["ids"]
        mapname = request.headers.get("X-QuakeLive-Map")

        if mapname is not None:
            return RedirectResponse(
                request.url_for(
                    "BalanceMapBased", mapname=mapname, ids=ids
                )
            )

    async def _get(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        return JSONResponse(await fetch(con, ids))


@bp.route("/map_based/{mapname}/{ids:steam_ids}")
class BalanceMapBased(Endpoint):
    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        pass

    async def _get(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        mapname = request.path_params["mapname"]
        return JSONResponse(await fetch(con, ids, mapname))


@bp.route("/with_qlstats_playerinfo/{ids:steam_ids}")
class BalanceWithQLStatsPlayerinfo(Endpoint):
    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        pass

    async def _get(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        return JSONResponse(await with_player_info_from_qlstats(con, ids))
