from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from qllr.endpoints import Endpoint
from qllr.templating import templates

from .methods import get_list


class RatingsJson(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        page = request.path_params.get("page", 0)
        gametype_id = request.path_params.get("gametype_id")
        return JSONResponse(await get_list(con, gametype_id, page))


class RatingsHtml(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        page = request.path_params.get("page", 0)
        gametype_id = request.path_params.get("gametype_id")
        show_inactive = request.query_params.get("show_inactive", False)
        if show_inactive:
            show_inactive = True

        context = await get_list(con, gametype_id, page, show_inactive)
        context["request"] = request
        context["current_page"] = page
        context["gametype"] = request.path_params["gametype"]
        context["show_inactive"] = show_inactive
        return templates.TemplateResponse("ratings_list.html", context)


routes = [
    Route("/{gametype}/{page:int}.json", endpoint=RatingsJson),
    Route("/{gametype}/", endpoint=RatingsHtml),
    Route("/{gametype}/{page:int}/", endpoint=RatingsHtml),
]
