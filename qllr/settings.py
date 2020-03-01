# -*- coding: utf-8 -*-

from starlette.config import Config
from starlette.datastructures import URL, CommaSeparatedStrings

config = Config(".env")

SUPPORTED_GAMETYPES = (
    'ad',
    'ca',
    'ctf',
    'ft',
    'tdm',
    'tdm2v2',
)
DATABASE_URL = str(config("DATABASE_URL", cast=URL))
HOST = config("HOST", default="127.0.0.1")
PORT = config("PORT", cast=int, default=7081)
TRUSTED_PROXIES = config("TRUSTED_PROXIES", cast=CommaSeparatedStrings, default=[])
PLAYER_COUNT_PER_PAGE = config("PLAYER_COUNT_PER_PAGE", cast=int, default=10)
RUN_POST_PROCESS = config("RUN_POST_PROCESS", cast=bool, default=True)
MOVING_AVG_COUNT = config("MOVING_AVG_COUNT", cast=int, default=50)
TWITCH_CLIENT_ID = config("TWITCH_CLIENT_ID", default="")

MIN_PLAYER_COUNT_IN_MATCH_TO_RATE = {}
USE_AVG_PERF = {}
for gt in SUPPORTED_GAMETYPES:
    MIN_PLAYER_COUNT_IN_MATCH_TO_RATE[gt] = config("MIN_PLAYER_COUNT_IN_MATCH_TO_RATE_{}".format(gt.upper()), cast=int, default=6)
    USE_AVG_PERF[gt] = config("USE_AVG_PERF_{}".format(gt.upper()), cast=bool, default=False)

MIN_PLAYER_COUNT_IN_MATCH_TO_RATE['tdm2v2'] = 4
