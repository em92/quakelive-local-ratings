from starlette.config import Config
from starlette.datastructures import URL, CommaSeparatedStrings
from trueskill import MU, SIGMA

config = Config(".env")

SUPPORTED_GAMETYPES = ("ad", "ca", "ctf", "ft", "tdm", "tdm2v2")
DATABASE_URL = str(config("DATABASE_URL", cast=URL))
HOST = config("HOST", default="127.0.0.1")
PORT = config("PORT", cast=int, default=8000)
TRUSTED_PROXIES = config("TRUSTED_PROXIES", cast=CommaSeparatedStrings, default=[])
PLAYER_COUNT_PER_PAGE = config("PLAYER_COUNT_PER_PAGE", cast=int, default=10)
RUN_POST_PROCESS = config("RUN_POST_PROCESS", cast=bool, default=True)
MOVING_AVG_COUNT = config("MOVING_AVG_COUNT", cast=int, default=50)
TWITCH_CLIENT_ID = config("TWITCH_CLIENT_ID", default="")
CACHE_HTTP_RESPONSE = config("CACHE_HTTP_RESPONSE", cast=bool, default=False)

INITIAL_R1_MEAN = {}
INITIAL_R1_DEVIATION = {}
MIN_PLAYER_COUNT_IN_MATCH_TO_RATE = {}
USE_AVG_PERF = {}
for gt in SUPPORTED_GAMETYPES:
    MIN_PLAYER_COUNT_IN_MATCH_TO_RATE[gt] = config(
        "MIN_PLAYER_COUNT_IN_MATCH_TO_RATE_{}".format(gt.upper()), cast=int, default=6
    )
    USE_AVG_PERF[gt] = config(
        "USE_AVG_PERF_{}".format(gt.upper()), cast=bool, default=False
    )
    INITIAL_R1_MEAN[gt] = config(
        "INITIAL_R1_MEAN_{}".format(gt.upper()), cast=float, default=MU
    )
    INITIAL_R1_DEVIATION[gt] = config(
        "INITIAL_R2_DEVIATION_{}".format(gt.upper()), cast=float, default=SIGMA
    )

INITIAL_R2_VALUE = INITIAL_R1_MEAN.copy()
MIN_PLAYER_COUNT_IN_MATCH_TO_RATE["tdm2v2"] = 4

AVG_PERF_GAMETYPES = [gt for gt in SUPPORTED_GAMETYPES if USE_AVG_PERF[gt]]
