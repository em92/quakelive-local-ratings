# -*- coding: utf-8 -*-

from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles

from . import blueprints as bp, submission
from .app import App
from .db import cache, get_db_pool
from .settings import RUN_POST_PROCESS
from .templating import templates

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


@app.on_event("startup")
async def on_startup():
    if RUN_POST_PROCESS is False:  # pragma: nocover
        return

    await cache.init()
    templates.env.globals["gametype_names"] = cache.GAMETYPE_NAMES

    dbpool = await get_db_pool()
    con = await dbpool.acquire()
    tr = con.transaction()
    await tr.start()

    try:
        await submission.run_post_process(con)
        await tr.commit()
    finally:
        await dbpool.release(con)


@app.route("/")
def http_root(request: Request):
    return RedirectResponse(request.url_for("MatchesHtml"))
