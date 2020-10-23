from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from qllr.endpoints import Endpoint

from ..player import PlayerEndpoint
from .methods import get_player_info_old


class DeprecatedPlayerJson(PlayerEndpoint):
    async def get_document(self, request: Request, con: Connection):
        steam_id = request.path_params["steam_id"]
        return JSONResponse(await get_player_info_old(con, steam_id))


routes = [Route("/player/{steam_id:int}.json", endpoint=DeprecatedPlayerJson)]
