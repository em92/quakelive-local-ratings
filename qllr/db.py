# -*- coding: utf-8 -*-
#

from collections import OrderedDict, MutableMapping
from urllib.parse import urlparse
import os

import psycopg2
from asyncpg import pool, create_pool, Connection
from .common import run_sync

from .conf import settings


async def get_db_pool() -> pool:
    try:
        return get_db_pool.cache
    except AttributeError:
        get_db_pool.cache = await create_pool(
            dsn=os.environ.get("DATABASE_URL", settings["db_url"])
        )
        return get_db_pool.cache


def take_away_null_values(params: OrderedDict) -> OrderedDict:
    result = params.copy()
    for key, value in params.items():
        if value is None:
            del result[key]
    return result


def db_connect():
    result = urlparse(os.environ.get("DATABASE_URL", settings["db_url"]))
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

        dbpool = run_sync(get_db_pool())
        con = run_sync(dbpool.acquire())
        tr = con.transaction()
        run_sync(tr.start())

        try:
            run_sync(self._init(con))
        finally:
            run_sync(tr.rollback())
            run_sync(dbpool.release(con))

    async def _init(self, con: Connection):
        async for row in con.cursor("SELECT gametype_id, gametype_short, gametype_name FROM gametypes"):
            self._gametype_ids[row[1]] = row[0]
            self._gametype_names[row[1]] = row[2]

        self.LAST_GAME_TIMESTAMPS = SurjectionDict(self._gametype_ids)

        async for row in con.cursor("SELECT medal_id, medal_short FROM medals ORDER BY medal_id"):
            self._medal_ids[row[1]] = row[0]
            self._medals.append(row[1])

        async for row in con.cursor("SELECT weapon_id, weapon_short FROM weapons ORDER BY weapon_id"):
            self._weapon_ids[row[1]] = row[0]
            self._weapons.append(row[1])

        for gametype_short, gametype_id in self._gametype_ids.items():
            self.LAST_GAME_TIMESTAMPS[gametype_id] = 0
            r = await con.fetchval("SELECT timestamp FROM matches WHERE gametype_id = $1 ORDER BY timestamp DESC LIMIT 1", gametype_id)
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

    @property
    def LAST_GAME_TIMESTAMP(self):
        return max(self.LAST_GAME_TIMESTAMPS.values())


cache = Cache()
