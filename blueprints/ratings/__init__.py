# -*- coding: utf-8 -*-

from app import App
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.requests import Request
from endpoints import Endpoint
from .methods import get_list
from templating import templates

'''
@app.route("/ratings/<gametype>/")
@app.route("/ratings/<gametype>/<int:page>/")
@try304
def http_rating_gametype_page(gametype, page = 0):
  show_inactive = request.args.get("show_inactive", False, type=bool)
  return render_template("ratings_list.html", **rating.get_list( gametype, page, show_inactive ),
    gametype = gametype,
    current_page = page,
    show_inactive = show_inactive,
    page_suffix = ("?show_inactive=yes" if show_inactive else ""),
    page_prefix = "/ratings/" + gametype
  )


@app.route("/ratings/<gametype>/<int:page>.json")
@try304
def http_ratings_gametype_page_json(gametype, page):
  return jsonify( **rating.get_list( gametype, page ) )
'''
bp = App()


@bp.route("/{gametype}/{page:int}.json")
class RatingsJson(Endpoint):
    async def get(self, request: Request):
        page = request.path_params.get("page", 0)
        gametype = request.path_params.get("gametype")
        return JSONResponse(await get_list(gametype, page))


@bp.route("/{gametype}")
@bp.route("/{gametype}/{page:int}")
class RatingsHtml(Endpoint):
    async def get(self, request: Request):
        page = request.path_params.get("page", 0)
        gametype = request.path_params.get("gametype")
        show_inactive = request.query_params.get("show_inactive", False)
        if show_inactive:
            show_inactive = True

        context = await get_list(gametype, page, show_inactive)
        context['request'] = request
        return templates.TemplateResponse("ratings_list.html", context)
