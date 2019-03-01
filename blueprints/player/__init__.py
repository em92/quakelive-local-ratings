# -*- coding: utf-8 -*-

from app import App
from starlette.responses import JSONResponse
from starlette.requests import Request
from endpoints import Endpoint
from .methods import get_player_info
from templating import templates

bp = App()


@bp.route("/{steam_id:int}.json")
class PlayerJson(Endpoint):
    async def get(self, request: Request):
        steam_id = request.path_params['steam_id']
        return JSONResponse(await get_player_info(steam_id))


@bp.route("/{steam_id:int}")
class PlayerHtml(Endpoint):
    async def get(self, request: Request):
        steam_id = request.path_params['steam_id']
        context = await get_player_info(steam_id)
        context['request'] = request
        context['steam_id'] = str(steam_id)
        return templates.TemplateResponse("player_stats.html", context)
