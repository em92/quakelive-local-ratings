from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from qllr.blueprints.player.methods import get_player_info
from qllr.endpoints import NoCacheEndpoint
from qllr.templating import templates

class PlayerAdmin(NoCacheEndpoint):
    async def get_document(self, request: Request, con: Connection):
        steam_id = request.path_params["steam_id"]
        context = await get_player_info(con, steam_id)
        context["request"] = request
        context["steam_id"] = str(steam_id)
        context["admin_mode"] = True
        return templates.TemplateResponse("player_admin.html", context)


routes = [Route("/player/{steam_id:int}", endpoint=PlayerAdmin)]
