# -*- coding: utf-8 -*-

from app import App
from starlette.responses import JSONResponse
from starlette.requests import Request
from endpoints import Endpoint
from .methods import get_scoreboard
from templating import templates

bp = App()


@bp.route("/{match_id:match_id}.json")
class ScoreboardJson(Endpoint):
    async def get(self, request: Request):
        match_id = request.path_params['match_id']
        return JSONResponse(await get_scoreboard(match_id))


@bp.route("/{match_id:match_id}")
class ScoreboardJson(Endpoint):
    async def get(self, request: Request):
        match_id = request.path_params['match_id']
        context = await get_scoreboard(match_id)
        context['request'] = request
        context['match_id'] = match_id
        return templates.TemplateResponse("scoreboard.html", context)
