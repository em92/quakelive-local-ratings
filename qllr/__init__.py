# -*- coding: utf-8 -*-

from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from . import blueprints as bp
from .app import App

app = App(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/elo", bp.balance_api)
app.mount("/stats", bp.submission)
app.mount("/scoreboard", bp.scoreboard)
app.mount("/player", bp.player)
app.mount("/ratings", bp.ratings)
app.mount("/matches", bp.matches)
app.mount("/steam_api", bp.steam_api)
app.mount("/export_rating", bp.export_rating)
app.mount("/deprecated", bp.deprecated)


@app.route("/")
def http_root(request: Request):
    return RedirectResponse(request.url_for("MatchesHtml"))
