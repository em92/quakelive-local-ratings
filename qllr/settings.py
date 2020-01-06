# -*- coding: utf-8 -*-

from starlette.config import Config
from starlette.datastructures import URL, CommaSeparatedStrings

config = Config(".env")

DATABASE_URL = str(config("DATABASE_URL", cast=URL))
HOST = config("HOST", default="127.0.0.1")
PORT = config("PORT", cast=int, default=7081)
TRUSTED_PROXIES = config("TRUSTED_PROXIES", cast=CommaSeparatedStrings, default=[])
PLAYER_COUNT_PER_PAGE = config("PLAYER_COUNT_PER_PAGE", cast=int, default=10)
RUN_POST_PROCESS = config("RUN_POST_PROCESS", cast=bool, default=True)
MIN_PLAYER_COUNT_IN_MATCH_TO_RATE = {
    "ad": config("MIN_PLAYER_COUNT_IN_MATCH_TO_RATE_AD", cast=int, default=6),
    "ca": config("MIN_PLAYER_COUNT_IN_MATCH_TO_RATE_CA", cast=int, default=6),
    "ctf": config("MIN_PLAYER_COUNT_IN_MATCH_TO_RATE_CTF", cast=int, default=6),
    "ft": config("MIN_PLAYER_COUNT_IN_MATCH_TO_RATE_FT", cast=int, default=6),
    "tdm": config("MIN_PLAYER_COUNT_IN_MATCH_TO_RATE_TDM", cast=int, default=6),
    "tdm2v2": 4,
}
MOVING_AVG_COUNT = config("MOVING_AVG_COUNT", cast=int, default=50)
USE_AVG_PERF = {
    "ad": config("USE_AVG_PERF_AD", cast=bool, default=False),
    "ca": config("USE_AVG_PERF_CA", cast=bool, default=False),
    "ctf": config("USE_AVG_PERF_CTF", cast=bool, default=False),
    "ft": config("USE_AVG_PERF_FT", cast=bool, default=False),
    "tdm": config("USE_AVG_PERF_TDM", cast=bool, default=False),
    "tdm2v2": config("USE_AVG_PERF_TDM2V2", cast=bool, default=False),
}
TWITCH_CLIENT_ID = config("TWITCH_CLIENT_ID", default="")
