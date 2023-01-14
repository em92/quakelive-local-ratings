from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import blueprints as bp, submission
from .app import App
from .db import cache, get_db_pool
from .settings import RUN_POST_PROCESS
from .templating import templates


def http_root(request: Request):
    return RedirectResponse(request.url_for("MatchesHtml"))


def http_about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})


def http_favicon(request: Request):
    return RedirectResponse(request.url_for("static", path="images/favicon.png"))


# fmt: off
http_robots_txt = PlainTextResponse("""
User-agent: *
Disallow: /
""")

routes = [
    Route("/about", endpoint=http_about),
    Route("/favicon.ico", endpoint=http_favicon),
    Mount("/static", StaticFiles(directory="static"), name="static"),
    Mount("/elo", routes=bp.balance_api.routes),
    Mount("/player", routes=bp.player.routes),
    Mount("/stats", routes=bp.submission.routes),
    Mount("/scoreboard", routes=bp.scoreboard.routes),
    Mount("/ratings", routes=bp.ratings.routes),
    Mount("/matches", routes=bp.matches.routes),
    Mount("/steam_api", routes=bp.steam_api.routes),
    Mount("/export_rating", routes=bp.export_rating.routes),
    Mount("/deprecated", routes=bp.deprecated.routes),
    Route("/robots.txt", endpoint=http_robots_txt),
    Route("/", endpoint=http_root),
]
# fmt: on

app = App(debug=True, routes=routes)


@app.on_event("startup")
async def on_startup():
    await cache.init()
    templates.env.globals["gametype_names"] = cache.GAMETYPE_NAMES

    if RUN_POST_PROCESS is False:  # pragma: nocover
        return

    dbpool = await get_db_pool()
    con = await dbpool.acquire()
    tr = con.transaction()
    await tr.start()

    try:
        await submission.run_post_process(con)
        await tr.commit()
    finally:
        await dbpool.release(con)
