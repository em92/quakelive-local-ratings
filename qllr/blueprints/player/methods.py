import json
from functools import reduce
from typing import Optional

from asyncpg import Connection

from qllr.common import DATETIME_FORMAT, clean_name, convert_timestamp_to_tuple
from qllr.db import cache
from qllr.exceptions import MatchNotFound, PlayerNotFound
from qllr.settings import MOVING_AVG_COUNT


async def get_player_info_mod_date(
    con: Connection, steam_id: int, gametype_id: Optional[int] = None
):

    query = """
    SELECT MAX(last_played_timestamp)
    FROM gametype_ratings
    WHERE steam_id = $1
    """

    params = [steam_id]

    if gametype_id is not None:
        query += " AND gametype_id = $2"
        params.append(gametype_id)

    return convert_timestamp_to_tuple(await con.fetchval(query, *params))


async def get_player_info(con: Connection, steam_id: int):

    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )

    def choose_rating_values(item: dict):
        if cache.USE_AVG_PERF[item["gametype_short"]]:
            item["rating"] = item["r2_value"]
            item["rating_d"] = 0
        else:
            item["rating"] = item["r1_mean"]
            item["rating_d"] = item["r1_deviation"]

        del item["r1_mean"]
        del item["r1_deviation"]
        del item["r2_value"]
        return item

    # player name, rating and games played
    query = """
    SELECT json_build_object(
        'name', p.name,
        'ratings', COALESCE(t.ratings, '{ }')
    )
    FROM players p
    LEFT JOIN (
        SELECT gr.steam_id, array_agg( json_build_object(
            'r1_mean',      CAST( ROUND( CAST(gr.r1_mean      AS NUMERIC), 2) AS REAL ),
            'r1_deviation', CAST( ROUND( CAST(gr.r1_deviation AS NUMERIC), 2) AS REAL ),
            'r2_value',     CAST( ROUND( CAST(gr.r2_value     AS NUMERIC), 2) AS REAL ),
            'n', gr.n,
            'gametype_short', g.gametype_short,
            'gametype', g.gametype_name
        ) ORDER by gr.n DESC ) AS ratings
        FROM gametype_ratings gr
        LEFT JOIN gametypes g ON g.gametype_id = gr.gametype_id
        WHERE gr.steam_id = $1
        GROUP BY gr.steam_id
    ) t ON p.steam_id = t.steam_id
    WHERE p.steam_id = $1
    """
    result = await con.fetchval(query, steam_id)
    if result is None:
        raise PlayerNotFound(steam_id)

    result["ratings"] = list(map(choose_rating_values, result["ratings"]))

    # weapon stats (frags + acc)
    query = """
    SELECT array_agg(json_build_object(
        'name', w.weapon_name,
        'short', w.weapon_short,
        'frags', t2.frags,
        'acc', t.accuracy
    ) ORDER BY t.weapon_id ASC)
    FROM (
        SELECT
            weapon_id,
            CASE
                WHEN SUM(shots) = 0 THEN 0
                ELSE CAST(100. * SUM(hits) / SUM(shots) AS INT)
            END AS accuracy
        FROM (
            SELECT weapon_id, frags, hits, shots
            FROM scoreboards_weapons sw
            LEFT JOIN ( -- TODO: need to change from LEFT JOIN to WHERE match_id IN
                SELECT m.match_id
                FROM matches m
                LEFT JOIN scoreboards s ON s.match_id = m.match_id
                WHERE steam_id = $2
                ORDER BY timestamp DESC LIMIT $1
            ) m ON m.match_id = sw.match_id
            WHERE sw.steam_id = $2
        ) sw
        GROUP BY weapon_id
    ) t
    LEFT JOIN weapons w ON t.weapon_id = w.weapon_id
    LEFT JOIN (
        SELECT
            weapon_id,
            SUM(frags) AS frags
        FROM scoreboards_weapons sw
        WHERE steam_id = $2
        GROUP BY weapon_id
    ) t2 ON t2.weapon_id = t.weapon_id
    """
    # TODO: cover case, where weapon_status is empty array
    result["weapon_stats"] = await con.fetchval(query, MOVING_AVG_COUNT, steam_id) or []

    # fav map
    query = """
    SELECT map_name
    FROM (
        SELECT map_id, COUNT(*) AS n
        FROM matches m
        WHERE match_id IN (SELECT match_id FROM scoreboards WHERE steam_id = $1)
        GROUP BY map_id
    ) t
    LEFT JOIN maps ON maps.map_id = t.map_id
    ORDER BY n DESC, maps.map_id ASC
    LIMIT 1
    """
    row = await con.fetchval(query, steam_id)
    fav_map = "None"
    if row is not None:
        fav_map = row

    fav_gt = "None"
    if len(result["ratings"]) > 0:
        fav_gt = result["ratings"][0]["gametype"]

    result["fav"] = {
        "map": fav_map,
        "gt": fav_gt,
        "wpn": reduce(
            lambda sum, x: sum if sum["frags"] > x["frags"] else x,
            result["weapon_stats"],
            {"frags": 0, "name": "None"},
        )["name"],
    }

    # 10 last matches
    query = """
    SELECT
        array_agg(json_build_object(
            'match_id', m.match_id,
            'datetime', to_char(to_timestamp(timestamp), '{DATETIME_FORMAT}'),
            'timestamp', timestamp,
            'gametype', g.gametype_short,
            'result', CASE
                WHEN m.team1_score > m.team2_score AND m.team = 1 THEN 'Win'
                WHEN m.team1_score < m.team2_score AND m.team = 2 THEN 'Win'
                ELSE 'Loss'
            END,
        'team1_score', m.team1_score,
        'team2_score', m.team2_score,
        'map', mm.map_name
        ) ORDER BY timestamp DESC) AS matches
    FROM(
        SELECT s.steam_id, s.team, m.*
        FROM scoreboards s
        LEFT JOIN matches m ON s.match_id = m.match_id
        WHERE s.steam_id = $1
        ORDER BY timestamp DESC
        LIMIT 10
    ) m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN maps mm ON mm.map_id = m.map_id
    """.format(
        DATETIME_FORMAT=DATETIME_FORMAT
    )

    result["matches"] = await con.fetchval(query, steam_id)

    return {"response": result, "title": clean_name(result["name"])}


async def get_best_match_of_player(
    con: Connection, steam_id: int, gametype_id: int
) -> str:

    query = """
    SELECT s.match_id::text
    FROM scoreboards s
    WHERE match_id IN (
        SELECT match_id
        FROM matches
        WHERE gametype_id = $1
    ) AND
    match_perf IS NOT NULL AND
    alive_time >= 1200 AND
    steam_id = $2
    ORDER BY match_perf DESC
    LIMIT 1
    """
    result = await con.fetchval(query, gametype_id, steam_id)

    if result is None:
        raise MatchNotFound("could not detect player's best match")

    return result
