# -*- coding: utf-8 -*-

from typing import Tuple

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse

from qllr.app import App
from qllr.endpoints import Endpoint
from qllr.templating import templates

from .methods import get_last_matches

bp = App()


@bp.route("/")
@bp.route("/{gametype}/")
@bp.route("/{gametype}/{page:int}/")
@bp.route("/player/{steam_id:int}/")
@bp.route("/player/{steam_id:int}/{gametype}/")
@bp.route("/player/{steam_id:int}/{gametype}/{page:int}/")
@bp.route("/player/{steam_id:int}/{page:int}/")
@bp.route("/{page:int}/")
class MatchesHtml(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        gametype = request.path_params.get("gametype", None)
        page = request.path_params.get("page", 0)
        steam_id = request.path_params.get("steam_id", None)

        context = await get_last_matches(con, gametype, steam_id, page)
        context["request"] = request
        context["gametype"] = gametype
        context["current_page"] = page
        context["steam_id"] = steam_id
        return templates.TemplateResponse("match_list.html", context)
