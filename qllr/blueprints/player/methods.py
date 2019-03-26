import json
from qllr.common import DATETIME_FORMAT, clean_name
from asyncpg import Connection
from functools import reduce
from qllr.conf import settings
from qllr.exceptions import PlayerNotFound


MOVING_AVG_COUNT = settings["moving_average_count"]


async def get_player_info(con: Connection, steam_id: int):

    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )

    # player name, rating and games played
    query = """
    SELECT json_build_object(
        'name', p.name,
        'ratings', COALESCE(t.ratings, '{ }')
    )
    FROM players p
    LEFT JOIN (
        SELECT gr.steam_id, array_agg( json_build_object(
            'rating',   CAST( ROUND( CAST(gr.mean      AS NUMERIC), 2) AS REAL ),
            'rating_d', CAST( ROUND( CAST(gr.deviation AS NUMERIC), 2) AS REAL ),
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
    result["weapon_stats"] = await con.fetchval(query, MOVING_AVG_COUNT, steam_id)

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
    ORDER BY maps.map_id ASC, n DESC
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

    return {"response": result, "title": clean_name(result["name"]), "ok": True}
