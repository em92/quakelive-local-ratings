from typing import Tuple

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from qllr.endpoints import Endpoint
from qllr.templating import templates

from .methods import get_best_matches_of_player, get_last_matches


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


class BestMatchesHtml(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        gametype = request.path_params["gametype"]
        steam_id = request.path_params["steam_id"]

        context = await get_best_matches_of_player(con, steam_id, gametype)
        context["request"] = request
        context["gametype"] = gametype
        context["steam_id"] = steam_id
        return templates.TemplateResponse("match_list.html", context)


routes = [
    Route("/", endpoint=MatchesHtml),
    Route("/{page:int}/", endpoint=MatchesHtml),
    Route("/player/{steam_id:int}/", endpoint=MatchesHtml),
    Route("/player/{steam_id:int}/{page:int}/", endpoint=MatchesHtml),
    Route("/player/{steam_id:int}/{gametype}/", endpoint=MatchesHtml),
    Route("/player/{steam_id:int}/{gametype}/{page:int}/", endpoint=MatchesHtml),
    Route("/player/{steam_id:int}/{gametype}/top", endpoint=BestMatchesHtml),
    Route("/{gametype}/", endpoint=MatchesHtml),
    Route("/{gametype}/{page:int}/", endpoint=MatchesHtml),
]
