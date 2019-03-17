#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from db import create_pool

from starlette.middleware.wsgi import WSGIMiddleware
from starlette.staticfiles import StaticFiles

from app import App
from old_main import app as old_app

app = App(debug=True)
app.mount('/static', StaticFiles(directory="static"), name='static')

import blueprints as bp
app.mount('/elo', bp.balance_api)
app.mount('/stats', bp.submission)
app.mount('/scoreboard', bp.scoreboard)
app.mount('/player', bp.player)
app.mount('/ratings', bp.ratings)
app.mount('/matches', bp.matches)
app.mount('/steam_api', bp.steam_api)
app.mount('', WSGIMiddleware(old_app.wsgi_app))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
