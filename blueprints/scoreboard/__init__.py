# -*- coding: utf-8 -*-

from app import App
from starlette.responses import JSONResponse, RedirectResponse
from starlette.requests import Request
from endpoints import Endpoint
from .methods import get_scoreboard

bp = App()

@bp.route("/{match_id:match_id}.json")
class ScoreboardJson(Endpoint):
    async def get(self, request):
        match_id = request.path_params['match_id']
        return JSONResponse(await get_scoreboard(match_id))

'''
@app.route("/scoreboard/<match_id>")
@try304
def http_scoreboard_match_id(match_id):
  return render_template("scoreboard.html", match_id = match_id, **rating.get_scoreboard( match_id ))
@bp.route("/{ids:steam_ids}")
async def http_elo(request: Request):
    ids = request.path_params['ids']
    try:
        return RedirectResponse(request.url_for(
            'http_elo_map',
            gametype=request.headers['X-QuakeLive-Gametype'],
            mapname=request.headers['X-QuakeLive-Map'],
            ids=ids
        ))
    except KeyError:
        return JSONResponse(await simple(ids))
'''