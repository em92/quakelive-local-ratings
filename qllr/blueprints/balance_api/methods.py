# -*- coding: utf-8 -*-

import typing

import requests
from asyncpg import Connection

from qllr.common import log_exception
from qllr.db import cache
from qllr.submission import get_map_id

AVG_PERF_GAMETYPE_IDS = cache.AVG_PERF_GAMETYPE_IDS
USE_AVG_PERF = cache.USE_AVG_PERF


COMMON_RATINGS_SQL = '''
SELECT
    steam_id,
    gametype_short,
    CASE WHEN gr.gametype_id = ANY($2) THEN r2_value ELSE r1_mean END AS rating,
    n
FROM
    gametype_ratings gr
LEFT JOIN
    gametypes gt ON gr.gametype_id = gt.gametype_id
WHERE
    steam_id = ANY($1)
'''

MAP_BASED_RATINGS_SQL = '''
SELECT
    steam_id,
    gametype_short,
    (1-w)*rating+w*map_rating,
    n
FROM (
    SELECT
        gr.steam_id,
        gr.rating, COALESCE(mgr.rating, 0) AS map_rating,
        COALESCE(mgr.n, 0) AS n,
        LEAST(0.25, (COALESCE(mgr.n, 0)/100.0)) AS w,
        gr.gametype_id
    FROM (
        SELECT
            steam_id,
            gametype_id,
            CASE WHEN gametype_id = ANY($2) THEN r2_value ELSE r1_mean END AS rating,
            n
        FROM
            gametype_ratings
    ) gr
    LEFT JOIN (
        SELECT
            steam_id,
            gametype_id,
            CASE WHEN gametype_id = ANY($2) THEN r2_value ELSE r1_mean END AS rating,
            n
        FROM map_gametype_ratings
        WHERE map_id = $3
    ) mgr ON mgr.gametype_id = gr.gametype_id AND mgr.steam_id = gr.steam_id
    WHERE
        gr.steam_id = ANY($1)
) gr
LEFT JOIN
    gametypes gt ON gr.gametype_id = gt.gametype_id
'''


def prepare_result(players):
    playerinfo = {}

    for steam_id, data in players.items():
        playerinfo[steam_id] = {
            "deactivated": False,
            "ratings": data.copy(),
            "allowRating": True,
            "privacy": "public",
        }

    return {
        "ok": True,
        "playerinfo": playerinfo,
        "players": list(players.values()),
        "untracked": [],
        "deactivated": [],
    }


async def fetch(con: Connection, steam_ids: typing.List[int], mapname: typing.Optional[str] = None):
    """
    Outputs player ratings compatible with balance.py plugin from minqlx-plugins
    """
    players = {}

    if mapname:
        map_id = await get_map_id(con, mapname, False)
        query = MAP_BASED_RATINGS_SQL
        query_args = (steam_ids, AVG_PERF_GAMETYPE_IDS, map_id)
    else:
        query = COMMON_RATINGS_SQL
        query_args = (steam_ids, AVG_PERF_GAMETYPE_IDS)

    async for row in con.cursor(query, *query_args):
        steam_id, gametype, rating, n = (str(row[0]), row[1], round(row[2], 2), row[3])
        if steam_id not in players:
            players[steam_id] = {"steamid": steam_id}
        players[steam_id][gametype] = {"games": n, "elo": rating}

    return prepare_result(players)


async def with_player_info_from_qlstats(con: Connection, steam_ids: typing.List[int]):
    result = await fetch(con, steam_ids)

    # TODO: need async version of this call
    # TODO: use request.Session() with adapter for testing
    try:
        r = requests.get(
            "http://qlstats.net/elo/" + "+".join(map(lambda id_: str(id_), steam_ids)),
            timeout=5,
        )
    except requests.exceptions.RequestException:
        return result

    if not r.ok:
        return result

    try:
        qlstats_data = r.json()
    except Exception as e:
        log_exception(e)
        return result

    qlstats_data["players"] = result["players"]
    for steam_id, info in result["playerinfo"].items():
        qlstats_data["playerinfo"][steam_id]["ratings"] = info["ratings"]

    return qlstats_data
