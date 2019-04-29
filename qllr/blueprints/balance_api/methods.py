# -*- coding: utf-8 -*-

import typing

import requests
from asyncpg import Connection

from qllr.common import log_exception
from qllr.db import cache
from qllr.exceptions import InvalidGametype
from qllr.settings import MOVING_AVG_COUNT
from qllr.submission import get_map_id

GAMETYPE_IDS = cache.GAMETYPE_IDS


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


async def simple(con: Connection, steam_ids: typing.List[int]):
    """
    Outputs player ratings compatible with balance.py plugin from minqlx-plugins

    Args:
        steam_ids (list): array of steam ids

    Returns:
        {
            "ok": True
            "players": [...],
            "deactivated": []
        }
    """
    players = {}

    query = """
    SELECT
        steam_id, gametype_short, mean, n
    FROM
        gametype_ratings gr
    LEFT JOIN
        gametypes gt ON gr.gametype_id = gt.gametype_id
    WHERE
        steam_id = ANY($1)"""
    async for row in con.cursor(query, steam_ids):
        steam_id, gametype, rating, n = (str(row[0]), row[1], round(row[2], 2), row[3])
        if steam_id not in players:
            players[steam_id] = {"steamid": steam_id}
        players[steam_id][gametype] = {"games": n, "elo": rating}

    return prepare_result(players)


async def with_player_info_from_qlstats(con: Connection, steam_ids: typing.List[int]):
    result = await simple(con, steam_ids)

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


async def for_certain_map(
    con: Connection, steam_ids: typing.List[int], gametype: str, mapname: str
):
    """
    Outputs player ratings compatible with balance.py plugin from miqlx-plugins

    Args:
        steam_ids (list): array of steam ids
        gametype (str): short gametype
        mapname (str): short mapname

    Returns:
        on success:
        {
            "ok": True
            "players": [...],
            "deactivated": []
        }
    """
    players = {}

    try:
        gametype_id = GAMETYPE_IDS[gametype]
    except KeyError:
        raise InvalidGametype(gametype)

    # checking, if map is played ever?
    map_id = await get_map_id(con, mapname, False)

    query = """
    SELECT
        steam_id,
        gametype_short,
        (1-w)*rating+w*map_rating,
        n
    FROM (
        SELECT
            gr.steam_id,
            gr.mean AS rating, COALESCE(mgr.r1_mean, 0) AS map_rating,
            COALESCE(mgr.n, 0) AS n,
            LEAST(1, (COALESCE(mgr.n, 0)/{MOVING_AVG_COUNT})::integer) AS w,
            gr.gametype_id
        FROM
            gametype_ratings gr
        LEFT JOIN (
            SELECT *
            FROM map_gametype_ratings
            WHERE map_id = $2
        ) mgr ON mgr.gametype_id = gr.gametype_id AND mgr.steam_id = gr.steam_id
        WHERE
            gr.steam_id = ANY($1)
    ) gr
    LEFT JOIN
        gametypes gt ON gr.gametype_id = gt.gametype_id
    """.format(MOVING_AVG_COUNT=int(MOVING_AVG_COUNT))
    async for row in con.cursor(query, steam_ids, map_id):
        steam_id, gametype, rating, n = (str(row[0]), row[1], round(row[2], 2), row[3])
        if steam_id not in players:
            players[steam_id] = {"steamid": steam_id}
        players[steam_id][gametype] = {"games": n, "elo": rating}

    return prepare_result(players)

    # TODO: переписать. 8 игроков - 16 запросов
    players = {}

    try:
        gametype_id = GAMETYPE_IDS[gametype]
    except KeyError:
        raise InvalidGametype(gametype)

    query_template = """
        SELECT
            AVG(t.match_rating), MAX(t.n)
        FROM (
            SELECT
                s.match_perf as match_rating, count(*) OVER() AS n
            FROM
                scoreboards s
            LEFT JOIN matches m ON m.match_id = s.match_id
            WHERE s.steam_id = $1 AND m.gametype_id = $2 {CLAUSE}
            ORDER BY m.timestamp DESC
            LIMIT $3
        ) t;
     """

    query_common = query_template.replace("{CLAUSE}", "")
    query_by_map = query_template.replace("{CLAUSE}", "AND m.map_id = $4")

    # getting common perfomance
    for steam_id in steam_ids:
        row = await con.fetchrow(query_common, steam_id, gametype_id, MOVING_AVG_COUNT)
        if row[0] is None:
            continue
        steam_id = str(steam_id)
        rating = round(row[0], 2)
        if steam_id not in players:
            players[steam_id] = {"steamid": steam_id}
        players[steam_id][gametype] = {"games": 0, "elo": rating}

    # checking, if map is played ever?
    map_id = await get_map_id(con, mapname, False)
    if map_id is None:
        raise KeyError("Unknown map: " + mapname)

    # getting map perfomance
    for steam_id in steam_ids:
        row = row = await con.fetchrow(
            query_by_map, steam_id, gametype_id, MOVING_AVG_COUNT, map_id
        )
        if row[0] is None:
            continue
        steam_id = str(steam_id)
        rating = round(row[0], 2)
        n = row[1]
        players[steam_id][gametype] = {"games": n, "elo": rating}

    return prepare_result(players)
