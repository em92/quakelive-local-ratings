# -*- coding: utf-8 -*-
#

import asyncio
import functools
import logging
import traceback
from datetime import datetime

import requests

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


def log_exception(e):  # pragma: no cover
    logger.warn(traceback.format_exc())


def clean_name(name):
    for s in ["0", "1", "2", "3", "4", "5", "6", "7"]:
        name = name.replace("^" + s, "")

    if name == "":
        name = "unnamed"

    return name


def run_sync(f, *args, **kwargs):  # pragma: no cover
    annoying_event_loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(f, loop=annoying_event_loop)
    annoying_event_loop.run_until_complete(future)
    return future.result()


async def request(url: str) -> requests.Response:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, functools.partial(requests.get, url, timeout=5)
    )


def convert_timestamp_to_tuple(timestamp):
    if timestamp is None:
        return None
    return datetime.utcfromtimestamp(timestamp).timetuple()[0:6]
