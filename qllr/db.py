import asyncio
from collections import OrderedDict
from collections.abc import MutableMapping
from typing import List
from urllib.parse import urlparse

import psycopg2
from asyncpg import Connection, create_pool
from asyncpg.pool import Pool
from cachetools import LRUCache

from .settings import DATABASE_URL, USE_AVG_PERF


async def get_db_pool(event_loop=None) -> Pool:
    try:
        get_db_pool.cache
    except AttributeError:
        get_db_pool.cache = {}

    if event_loop is None:
        event_loop = asyncio.get_event_loop()

    try:
        return get_db_pool.cache[event_loop]
    except KeyError:
        get_db_pool.cache[event_loop] = await create_pool(
            dsn=DATABASE_URL, loop=event_loop
        )
        return get_db_pool.cache[event_loop]


def db_connect():  # pragma: nocover
    result = urlparse(DATABASE_URL)
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    return psycopg2.connect(
        database=database, user=username, password=password, host=hostname, port=port
    )


class SurjectionDict(MutableMapping):
    def __init__(self, surjection):
        self.surjection = surjection
        self.data = {}

    def transform(self, key):
        if key in self.surjection:
            key = self.surjection[key]
        return key

    def __iter__(self):
        return self.data.__iter__()

    def __len__(self):
        return self.data.__len__()

    def __setitem__(self, key, value):
        self.data[self.transform(key)] = value

    def __getitem__(self, key):
        return self.data[self.transform(key)]

    def __delitem__(self, key):
        return self.data.__delitem__(self.transform(key))

    def __repr__(self):
        return repr(self.data)


class Cache:
    _instance = None
    store = LRUCache(maxsize=100)

    def __new__(cls):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls)
        return cls._instance

    def __init__(self):
        self._gametype_ids = {}
        self._gametype_names = OrderedDict()
        self._medal_ids = {}
        self._medals = []
        self._weapon_ids = {}
        self._weapons = []
        self.LAST_GAME_TIMESTAMPS = {}

    async def init(self):
        dbpool = await get_db_pool()
        con = await dbpool.acquire()

        for row in await con.fetch(
            "SELECT gametype_id, gametype_short, gametype_name FROM gametypes"
        ):
            self._gametype_ids[row[1]] = row[0]
            self._gametype_names[row[1]] = row[2]

        self.LAST_GAME_TIMESTAMPS = SurjectionDict(self._gametype_ids)

        for row in await con.fetch(
            "SELECT medal_id, medal_short FROM medals ORDER BY medal_id"
        ):
            self._medal_ids[row[1]] = row[0]
            self._medals.append(row[1])

        for row in await con.fetch(
            "SELECT weapon_id, weapon_short FROM weapons ORDER BY weapon_id"
        ):
            self._weapon_ids[row[1]] = row[0]
            self._weapons.append(row[1])

        for gametype_short, gametype_id in self._gametype_ids.items():
            self.LAST_GAME_TIMESTAMPS[gametype_id] = 0
            # running several sql queries looks stupid, isn't it?
            r = await con.fetchval(
                "SELECT timestamp FROM matches WHERE gametype_id = $1 ORDER BY timestamp DESC LIMIT 1",
                gametype_id,
            )
            if r:
                self.LAST_GAME_TIMESTAMPS[gametype_id] = r

    @property
    def GAMETYPE_IDS(self):
        return self._gametype_ids.copy()

    @property
    def GAMETYPE_NAMES(self):
        return self._gametype_names.copy()

    @property
    def MEDAL_IDS(self):
        return self._medal_ids.copy()

    @property
    def MEDALS_AVAILABLE(self):
        return self._medals[:]

    @property
    def WEAPON_IDS(self):
        return self._weapon_ids.copy()

    @property
    def WEAPONS_AVAILABLE(self):
        return self._weapons[:]

    def LAST_GAME_TIMESTAMP(self, gametype: str) -> int:
        if gametype not in self.LAST_GAME_TIMESTAMPS:
            return max(self.LAST_GAME_TIMESTAMPS.values())

        return self.LAST_GAME_TIMESTAMPS[gametype]

    @property
    def USE_AVG_PERF(self):
        result = USE_AVG_PERF.copy()
        for gt, id in self._gametype_ids.items():
            result[id] = result[gt]
        return result

    @property
    def AVG_PERF_GAMETYPE_IDS(self) -> List[int]:
        result = []
        for gt, id in self._gametype_ids.items():
            if USE_AVG_PERF[gt]:
                result.append(id)
        return result

    def key(self, suffix, gametype=None):
        return "{0}_{1}_{2}".format(
            self.LAST_GAME_TIMESTAMP(gametype), gametype, suffix
        )


cache = Cache()


def rating_column(gametype) -> str:
    return "r2_value" if cache.USE_AVG_PERF[gametype] else "r1_mean"
