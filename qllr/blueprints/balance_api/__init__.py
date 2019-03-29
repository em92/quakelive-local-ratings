# -*- coding: utf-8 -*-

from typing import Optional

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from qllr.app import App
from qllr.endpoints import Endpoint

from .methods import for_certain_map, simple, with_player_info_from_qlstats

bp = App()
bp.json_only_mode = True


@bp.route("/{ids:steam_ids}")
class BalanceSimple(Endpoint):
    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        ids = request.path_params["ids"]
        gametype = request.headers.get("X-QuakeLive-Gametype")
        mapname = request.headers.get("X-QuakeLive-Map")

        if gametype is not None and mapname is not None:
            return RedirectResponse(
                request.url_for(
                    "BalanceMapBased", gametype=gametype, mapname=mapname, ids=ids
                )
            )

    async def _get(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        return JSONResponse(await simple(con, ids))


@bp.route("/map_based/{gametype}/{mapname}/{ids:steam_ids}")
class BalanceMapBased(Endpoint):
    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        pass

    async def _get(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        gametype = request.path_params["gametype"]
        mapname = request.path_params["mapname"]
        return JSONResponse(await for_certain_map(con, ids, gametype, mapname))


@bp.route("/with_qlstats_playerinfo/{ids:steam_ids}")
class BalanceWithQLStatsPlayerinfo(Endpoint):
    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        pass

    async def _get(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        return JSONResponse(await with_player_info_from_qlstats(con, ids))
