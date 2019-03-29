# -*- coding: utf-8 -*-
#

import asyncio
import logging
import traceback

DATETIME_FORMAT = "YYYY-MM-DD HH24:MI TZ"
MATCH_LIST_ITEM_COUNT = 25

logger = logging.getLogger("qllr")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S"
)
ch.setFormatter(formatter)

logger.addHandler(ch)


def log_exception(e):
    logger.warn(traceback.format_exc())


def clean_name(name):
    for s in ["0", "1", "2", "3", "4", "5", "6", "7"]:
        name = name.replace("^" + s, "")

    if name == "":
        name = "unnamed"

    return name


def run_sync(f, *args, **kwargs):
    annoying_event_loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(f, loop=annoying_event_loop)
    annoying_event_loop.run_until_complete(future)
    return future.result()
