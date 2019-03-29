# -*- coding: utf-8 -*-

from qllr.app import App
from starlette.responses import JSONResponse, RedirectResponse
from starlette.requests import Request
from qllr.endpoints import Endpoint, HTTPEndpoint
from .methods import get_player_info
from qllr.templating import templates
from asyncpg import Connection

bp = App()


@bp.route("/{steam_id:int}.json")
class PlayerJson(Endpoint):
    async def _get(self, request: Request, con: Connection):
        steam_id = request.path_params['steam_id']
        return JSONResponse(await get_player_info(con, steam_id))


@bp.route("/{steam_id:int}")
class PlayerHtml(Endpoint):
    async def _get(self, request: Request, con: Connection):
        steam_id = request.path_params['steam_id']
        context = await get_player_info(con, steam_id)
        context['request'] = request
        context['steam_id'] = str(steam_id)
        return templates.TemplateResponse("player_stats.html", context)


@bp.route("/{steam_id:int}/matches")
@bp.route("/{steam_id:int}/matches/")
@bp.route("/{steam_id:int}/matches/{page:int}/")
@bp.route("/{steam_id:int}/matches/{gametype}/")
@bp.route("/{steam_id:int}/matches/{gametype}/{page:int}/")
class PlayerMatchesDeprecatedRoute(HTTPEndpoint):
    async def get(self, request: Request):
        return RedirectResponse(
            request.url_for(
                "MatchesHtml",
                steam_id=request.path_params['steam_id'],
                page=request.path_params.get('page'),
                gametype=request.path_params.get('gametype'),
            )
        )
