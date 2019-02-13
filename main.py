#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys

#parser = argparse.ArgumentParser()
#parser.add_argument("-c", metavar="config.json", help="use the provided config file", default = "cfg.json")
#args = parser.parse_args()

from conf import settings as cfg
if not cfg.read_from_file( "cfg.json" ):
  sys.exit(1)

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.staticfiles import StaticFiles

from app import App
from old_main import app as old_app

app = App()
app.debug = True
app.mount('/static', StaticFiles(directory="static"), name='static')

import blueprints as bp
app.mount('/elo', bp.balance_api)
app.mount('/stats', bp.submission)
app.mount('', WSGIMiddleware(old_app.wsgi_app))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
