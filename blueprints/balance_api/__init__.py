# -*- coding: utf-8 -*-

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, RedirectResponse

from .methods import simple, for_certain_map, with_player_info_from_qlstats

bp = Starlette()


@bp.exception_handler(HTTPException)
async def http_exception_handler(request, e):
    return JSONResponse({'ok': False, 'message': e.detail}, status_code=e.status_code)


@bp.exception_handler(500)
async def unhandled_exception_handler(request, e):
    return JSONResponse({'ok': False, 'message': type(e).__name__ + ": " + str(e)}, status_code=500)


@bp.route("/elo/{ids:steam_ids}")
@bp.route("/elo_b/{ids:steam_ids}")
def http_elo(request):
    ids = request.path_params['ids']
    print(ids)
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
