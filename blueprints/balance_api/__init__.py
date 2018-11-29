# -*- coding: utf-8 -*-

from app import App
from starlette.responses import JSONResponse, RedirectResponse

from .methods import simple, for_certain_map, with_player_info_from_qlstats

bp = App()


@bp.route("/elo/{ids:steam_ids}")
@bp.route("/elo_b/{ids:steam_ids}")
def http_elo(request):
    ids = request.path_params['ids']
    try:
        return RedirectResponse(bp.url_path_for(
            'http_elo_map',
            gametype=request.headers['X-QuakeLive-Gametype'],
            mapname=request.headers['X-QuakeLive-Map'],
            ids="+".join(ids)
        ))
    except KeyError:
        return JSONResponse(simple(ids))


@bp.route("/elo_map/{gametype}/{mapname}/{ids:steam_ids}")
def http_elo_map(request, gametype, mapname, ids):
    return JSONResponse(for_certain_map(ids, gametype, mapname))


@bp.route("/elo_with_qlstats_playerinfo/{ids:steam_ids}")
async def http_elo_with_qlstats_playerinfo(request, ids):
    return JSONResponse(with_player_info_from_qlstats(ids))
