from typing import Tuple

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from qllr.endpoints import Endpoint
from qllr.templating import templates

from .methods import get_scoreboard, get_scoreboard_mod_date


class ScoreboardEndpoint(Endpoint):
    async def get_last_doc_modified(self, request: Request, con: Connection) -> Tuple:
        return await get_scoreboard_mod_date(con, request.path_params["match_id"])


class ScoreboardJson(ScoreboardEndpoint):
    async def get_document(self, request: Request, con: Connection):
        match_id = request.path_params["match_id"]
        return JSONResponse(await get_scoreboard(con, match_id))


class ScoreboardHtml(ScoreboardEndpoint):
    async def get_document(self, request: Request, con: Connection):
        match_id = request.path_params["match_id"]
        context = await get_scoreboard(con, match_id)
        context["request"] = request
        context["match_id"] = match_id
        return templates.TemplateResponse("scoreboard.html", context)


routes = [
    Route("/{match_id:match_id}.json", endpoint=ScoreboardJson),
    Route("/{match_id:match_id}", endpoint=ScoreboardHtml),
]
