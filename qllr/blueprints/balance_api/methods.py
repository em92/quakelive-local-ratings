# -*- coding: utf-8 -*-

import typing
import requests
from qllr.common import log_exception
from qllr.settings import MOVING_AVG_COUNT
from qllr.db import cache, get_db_pool
from qllr.exceptions import InvalidGametype
from qllr.submission import get_map_id

GAMETYPE_IDS = cache.GAMETYPE_IDS


def prepare_result(players):
    playerinfo = {}

    for steam_id, data in players.items():
        playerinfo[steam_id] = {
            'deactivated': False,
            'ratings': data.copy(),
            'allowRating': True,
            'privacy': "public"
        }

    return {
        "ok": True,
        "playerinfo": playerinfo,
        "players": list(players.values()),
        "untracked": [],
        "deactivated": []
    }


async def simple(steam_ids: typing.List[int]):
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
    dbpool = await get_db_pool()
    con = await dbpool.acquire()

    try:

        query = '''
        SELECT
            steam_id, gametype_short, mean, n
        FROM
            gametype_ratings gr
        LEFT JOIN
            gametypes gt ON gr.gametype_id = gt.gametype_id
        WHERE
            steam_id = ANY($1)'''
        rows = await con.fetch(query, steam_ids)
        for row in rows:
            steam_id = str(row[0])
            gametype = row[1]
            rating   = round(row[2], 2)
            n        = row[3]
            if steam_id not in players:
                players[steam_id] = {"steamid": steam_id}
            players[steam_id][gametype] = {"games": n, "elo": rating}

        result = prepare_result(players)

    finally:
        await dbpool.release(con)

    return result


async def with_player_info_from_qlstats(steam_ids: typing.List[int]):
    result = await simple(steam_ids)

    try:
        r = requests.get("http://qlstats.net/elo/" + "+".join(map(lambda id_: str(id_), steam_ids)), timeout=5)
    except requests.exceptions.RequestException:
        return result

    if not r.ok:
        return result

    try:
        qlstats_data = r.json()
    except Exception as e:
        log_exception(e)
        return result

    qlstats_data['players'] = result['players']
    for steam_id, info in result['playerinfo'].items():
        qlstats_data['playerinfo'][steam_id]['ratings'] = info['ratings']

    return qlstats_data


async def for_certain_map(steam_ids: typing.List[int], gametype: str, mapname: str):
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
    # TODO: переписать. 8 игроков - 16 запросов
    players = {}

    dbpool = await get_db_pool()
    con = await dbpool.acquire()

    try:
        gametype_id = GAMETYPE_IDS[gametype]
    except KeyError:
        raise InvalidGametype(gametype)

    try:

        query_template = '''
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
         '''

        query_common = query_template.replace("{CLAUSE}", "")
        query_by_map = query_template.replace("{CLAUSE}", "AND m.map_id = $4")

        # getting common perfomance
        for steam_id in steam_ids:
            row = await con.fetchrow(query_common, steam_id, gametype_id, MOVING_AVG_COUNT)
            if row[0] is None:
                continue
            steam_id = str(steam_id)
            rating   = round(row[0], 2)
            if steam_id not in players:
                players[steam_id] = {"steamid": steam_id}
            players[steam_id][gametype] = {"games": 0, "elo": rating}

        # checking, if map is played ever?
        map_id = await get_map_id(con, mapname, False)
        if map_id is None:
            raise KeyError("Unknown map: " + mapname)

        # getting map perfomance
        for steam_id in steam_ids:
            row = row = await con.fetchrow(query_by_map, steam_id, gametype_id, MOVING_AVG_COUNT, map_id)
            if row[0] is None:
                continue
            steam_id = str(steam_id)
            rating   = round(row[0], 2)
            n        = row[1]
            players[steam_id][gametype] = {"games": n, "elo": rating}

        result = prepare_result(players)

    finally:
        await dbpool.release(con)

    return result
