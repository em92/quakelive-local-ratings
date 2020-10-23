from typing import Tuple

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route

from qllr.app import App
from qllr.endpoints import Endpoint, HTTPEndpoint
from qllr.templating import templates

from .methods import get_best_match_of_player, get_player_info, get_player_info_mod_date

bp = App()


class PlayerEndpoint(Endpoint):
    async def get_last_doc_modified(self, request: Request, con: Connection) -> Tuple:
        return await get_player_info_mod_date(
            con, request.path_params["steam_id"], request.path_params.get("gametype_id")
        )


class PlayerJson(PlayerEndpoint):
    async def get_document(self, request: Request, con: Connection):
        steam_id = request.path_params["steam_id"]
        return JSONResponse(await get_player_info(con, steam_id))


class PlayerHtml(PlayerEndpoint):
    async def get_document(self, request: Request, con: Connection):
        steam_id = request.path_params["steam_id"]
        context = await get_player_info(con, steam_id)
        context["request"] = request
        context["steam_id"] = str(steam_id)
        return templates.TemplateResponse("player_stats.html", context)


class PlayerMatchesDeprecatedRoute(HTTPEndpoint):
    async def get(self, request: Request):
        return RedirectResponse(
            request.url_for(
                "MatchesHtml",
                steam_id=request.path_params["steam_id"],
                page=request.path_params.get("page"),
                gametype=request.path_params.get("gametype"),
            ),
            status_code=308,
        )


class BestMatchOfPlayerRedirect(PlayerEndpoint):
    async def get_document(self, request: Request, con: Connection):
        steam_id = request.path_params["steam_id"]
        gametype_id = request.path_params["gametype_id"]
        match_id = await get_best_match_of_player(con, steam_id, gametype_id)
        return RedirectResponse(request.url_for("ScoreboardHtml", match_id=match_id))


routes = [
    Route("/{steam_id:int}.json", endpoint=PlayerJson),
    Route("/{steam_id:int}", endpoint=PlayerHtml),
    Route("/{steam_id:int}/matches", endpoint=PlayerMatchesDeprecatedRoute),
    Route("/{steam_id:int}/matches/", endpoint=PlayerMatchesDeprecatedRoute),
    Route("/{steam_id:int}/matches/{page:int}/", endpoint=PlayerMatchesDeprecatedRoute),
    Route("/{steam_id:int}/matches/{gametype}/", endpoint=PlayerMatchesDeprecatedRoute),
    Route(
        "/{steam_id:int}/matches/{gametype}/{page:int}/",
        endpoint=PlayerMatchesDeprecatedRoute,
    ),
    Route("/{steam_id:int}/best_match/{gametype}", endpoint=BestMatchOfPlayerRedirect),
]
