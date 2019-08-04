# -*- coding: utf-8 -*-

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse

from qllr.app import App
from qllr.endpoints import Endpoint
from qllr.templating import templates

from .methods import get_scoreboard

bp = App()


@bp.route("/{match_id:match_id}.json")
class ScoreboardJson(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        match_id = request.path_params["match_id"]
        return JSONResponse(await get_scoreboard(con, match_id))


@bp.route("/{match_id:match_id}")
class ScoreboardHtml(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        match_id = request.path_params["match_id"]
        context = await get_scoreboard(con, match_id)
        context["request"] = request
        context["match_id"] = match_id
        return templates.TemplateResponse("scoreboard.html", context)
