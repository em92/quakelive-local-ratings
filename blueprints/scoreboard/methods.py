# -*- coding: utf-8 -*-

import json

from common import DATETIME_FORMAT
from db import get_db_pool
from exceptions import MatchNotFound


async def get_scoreboard(match_id: str):

    dbpool = await get_db_pool()
    con = await dbpool.acquire()
    await con.set_type_codec(
        'json',
        encoder=json.dumps,
        decoder=json.loads,
        schema='pg_catalog'
    )
    tr = con.transaction()
    await tr.start()

    try:
        query = """
        SELECT
            json_build_object(
                'gt_short',    g.gametype_short,
                'gt',          g.gametype_name,
                'factory',     f.factory_short,
                'map',         mm.map_name,
                'team1_score', m.team1_score,
                'team2_score', m.team2_score,
                'rating_diff', CAST( ROUND( CAST(t.diff AS NUMERIC), 2) AS REAL ),
                'timestamp',   m.timestamp,
                'datetime',    TO_CHAR(to_timestamp(m.timestamp), '{DATETIME_FORMAT}'),
                'duration',    TO_CHAR((m.duration || ' second')::interval, 'MI:SS')
            )
        FROM
            matches m
        LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
        LEFT JOIN factories f ON f.factory_id = m.factory_id
        LEFT JOIN maps mm ON m.map_id = mm.map_id
        LEFT JOIN (
            SELECT match_id, sum(rating) as diff
            FROM (
                SELECT match_id, team, avg(old_mean)*(case when team = 1 then 1 else -1 end) as rating
                FROM scoreboards
                WHERE match_perf is not NULL AND match_id = $1
                GROUP by match_id, team
            ) t
            GROUP by match_id
        ) t ON t.match_id = m.match_id
        WHERE
            m.match_id = $1;
        """.format(
            DATETIME_FORMAT=DATETIME_FORMAT
        )
        summary = await con.fetchval(query, match_id)
        if summary is None:
            raise MatchNotFound(match_id)

        query = """
        SELECT
            json_object_agg(t.steam_id, t.weapon_stats)
        FROM (
            SELECT
                t.steam_id::text,
                json_object_agg(t.weapon_short, ARRAY[t.frags, t.hits, t.shots]) AS weapon_stats
            FROM (
                SELECT
                    s.steam_id,
                    w.weapon_short,
                    SUM(sw.frags) AS frags,
                    SUM(sw.hits) AS hits,
                    SUM(sw.shots) AS shots
                FROM
                    scoreboards s
                RIGHT JOIN scoreboards_weapons sw ON sw.match_id = s.match_id AND sw.steam_id = s.steam_id AND sw.team = s.team
                LEFT JOIN weapons w ON w.weapon_id = sw.weapon_id
                WHERE
                    s.match_id = $1
                GROUP BY s.steam_id, w.weapon_short
            ) t
            GROUP BY t.steam_id
        ) t;
        """
        player_weapon_stats = await con.fetchval(query, match_id)

        query = """
        SELECT
            json_object_agg(t.steam_id, t.medal_stats)
        FROM (
            SELECT
                t.steam_id::text,
                json_object_agg(t.medal_short, t.count) AS medal_stats
            FROM (
                SELECT
                    s.steam_id,
                    m.medal_short,
                    SUM(sm.count) AS count
                FROM
                    scoreboards s
                RIGHT JOIN scoreboards_medals sm ON sm.match_id = s.match_id AND sm.steam_id = s.steam_id AND sm.team = s.team
                LEFT JOIN medals m ON m.medal_id = sm.medal_id
                WHERE
                    s.match_id = $1
                GROUP BY s.steam_id, m.medal_short
            ) t
            GROUP BY t.steam_id
        ) t;
        """
        player_medal_stats = await con.fetchval(query, match_id)

        query = """
        SELECT
            array_agg(item)
        FROM (
            SELECT
                json_build_object(
                    'steam_id', t.steam_id::text,
                    'team', t.team::text,
                    'name', p.name,
                    'stats', json_build_object(
                        'score',                t.score,
                        'frags',                t.frags,
                        'deaths',             t.deaths,
                        'damage_dealt', t.damage_dealt,
                        'damage_taken', t.damage_taken,
                        'alive_time',     t.alive_time
                    ),
                    'rating', json_build_object(
                        'old',     CAST( ROUND( CAST(t.old_mean            AS NUMERIC), 2) AS REAL ),
                        'old_d', CAST( ROUND( CAST(t.old_deviation AS NUMERIC), 2) AS REAL ),
                        'new',     CAST( ROUND( CAST(t.new_mean            AS NUMERIC), 2) AS REAL ),
                        'new_d', CAST( ROUND( CAST(t.new_deviation AS NUMERIC), 2) AS REAL )
                    ),
                    'medal_stats', ms.medal_stats,
                    'weapon_stats', ws.weapon_stats
                ) AS item
            FROM
                scoreboards t
            LEFT JOIN players p ON p.steam_id = t.steam_id
            LEFT JOIN (
                SELECT
                    t.steam_id, t.team,
                    json_object_agg(t.weapon_short, ARRAY[t.frags, t.hits, t.shots, t.accuracy]) AS weapon_stats
                FROM
                    (
                    SELECT
                        s.steam_id, s.team, w.weapon_short, sw.frags, sw.hits, sw.shots,
                        CASE WHEN sw.shots = 0 THEN 0
                            ELSE CAST(100. * sw.hits / sw.shots AS INT)
                        END AS accuracy
                    FROM
                        scoreboards s
                    RIGHT JOIN scoreboards_weapons sw ON sw.match_id = s.match_id AND sw.steam_id = s.steam_id AND sw.team = s.team
                    LEFT JOIN weapons w ON w.weapon_id = sw.weapon_id
                    WHERE
                        s.match_id = $1
                    ) t
                    GROUP BY t.steam_id, t.team
            ) ws ON ws.steam_id = t.steam_id AND ws.team = t.team
            LEFT JOIN (
                SELECT
                    t.steam_id, t.team,
                    json_object_agg(t.medal_short, t.count) AS medal_stats
                FROM (
                    SELECT
                        s.steam_id, s.team, m.medal_short, sm.count
                    FROM
                        scoreboards s
                    RIGHT JOIN scoreboards_medals sm ON sm.match_id = s.match_id AND sm.steam_id = s.steam_id AND sm.team = s.team
                    LEFT JOIN medals m ON m.medal_id = sm.medal_id
                    WHERE
                        s.match_id = $1
                ) t
                GROUP BY t.steam_id, t.team
            ) ms ON ms.steam_id = t.steam_id AND ms.team = t.team
            WHERE
                t.match_id = $1
            ORDER BY t.score DESC
        ) t
        """
        overall_stats = await con.fetchval(query, match_id)

        query = """
        SELECT
            array_agg(m.medal_short)
        FROM (
            SELECT DISTINCT medal_id
            FROM scoreboards_medals
            WHERE match_id = $1
            ) sm
         LEFT JOIN medals m ON m.medal_id = sm.medal_id
        """
        medals_available = await con.fetchval(query, match_id)

        query = """
        SELECT
            array_agg(w.weapon_short)
        FROM (
            SELECT DISTINCT weapon_id
            FROM scoreboards_weapons
            WHERE match_id = $1
        ) sw
        LEFT JOIN weapons w ON w.weapon_id = sw.weapon_id
        """
        weapons_available = await con.fetchval(query, match_id)

        result = {
            "summary": summary,
            "player_stats": {
                "weapons": player_weapon_stats,
                "medals": player_medal_stats,
            },
            "team_stats": {"overall": overall_stats},
            "weapons_available": weapons_available,
            "medals_available": medals_available,
            "ok": True,
        }
    finally:
        await tr.rollback()
        await dbpool.release(con)

    return result
