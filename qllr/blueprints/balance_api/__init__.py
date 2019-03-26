# -*- coding: utf-8 -*-

from qllr.app import App
from starlette.responses import JSONResponse, RedirectResponse
from starlette.requests import Request

from .methods import simple, for_certain_map, with_player_info_from_qlstats

bp = App()
bp.json_only_mode = True


@bp.route("/{ids:steam_ids}")
async def http_elo(request: Request):
    ids = request.path_params['ids']
    try:
        return RedirectResponse(request.url_for(
            'http_elo_map',
            gametype=request.headers['X-QuakeLive-Gametype'],
            mapname=request.headers['X-QuakeLive-Map'],
            ids=ids
        ))
    except KeyError:
        return JSONResponse(await simple(ids))


@bp.route("/map_based/{gametype}/{mapname}/{ids:steam_ids}")
async def http_elo_map(request: Request):
    ids = request.path_params['ids']
    gametype = request.path_params['gametype']
    mapname = request.path_params['mapname']
    return JSONResponse(await for_certain_map(ids, gametype, mapname))


@bp.route("/with_qlstats_playerinfo/{ids:steam_ids}")
async def http_elo_with_qlstats_playerinfo(request: Request):
    ids = request.path_params['ids']
    return JSONResponse(await with_player_info_from_qlstats(ids))
