# -*- coding: utf-8 -*-

from app import App
from starlette.responses import JSONResponse
from starlette.requests import Request
from endpoints import Endpoint
from .methods import get_last_matches
from templating import templates

bp = App()


'''
@app.route("/player/<int:steam_id>/matches/")
@app.route("/player/<int:steam_id>/matches/<int:page>/")
@app.route("/player/<int:steam_id>/matches/<gametype>/")
@app.route("/player/<int:steam_id>/matches/<gametype>/<int:page>/")
'''


@bp.route("/")
@bp.route("/{gametype}")
@bp.route("/{gametype}/{page:int}")
@bp.route("/player/{steam_id:int}")
@bp.route("/player/{steam_id:int}/{gametype}")
@bp.route("/player/{steam_id:int}/{gametype}/{page:int}")
@bp.route("/player/{steam_id:int}/{page:int}")
@bp.route("/{page:int}")
class MatchesHtml(Endpoint):
    async def get(self, request: Request):
        gametype = request.path_params.get('gametype', None)
        page = request.path_params.get("page", 0)
        steam_id = request.path_params.get("steam_id", None)

        context = await get_last_matches(gametype, steam_id, page)
        context['request'] = request
        context['gametype'] = gametype
        context['current_page'] = page
        return templates.TemplateResponse("match_list.html", context)
