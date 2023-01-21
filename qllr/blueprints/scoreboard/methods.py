import json

from asyncpg import Connection

from qllr.common import DATETIME_FORMAT, convert_timestamp_to_tuple
from qllr.exceptions import MatchNotFound
from qllr.gametypes import GAMETYPE_RULES
from qllr.settings import USE_AVG_PERF


async def get_medals_available(con: Connection, match_id: str):
    query = """
    SELECT
        COALESCE(array_agg(m.medal_short ORDER BY m.medal_id ASC), '{ }')
    FROM (
        SELECT DISTINCT medal_id
        FROM scoreboards_medals
        WHERE match_id = $1
        ) sm
     LEFT JOIN medals m ON m.medal_id = sm.medal_id
    """
    return await con.fetchval(query, match_id)


async def get_scoreboard_mod_date(con: Connection, match_id: str):
    query = """
    SELECT MAX(last_played_timestamp)
    FROM gametype_ratings
    WHERE steam_id IN (
        SELECT steam_id
        FROM scoreboards
        WHERE match_id = $1
    )
    """

    return convert_timestamp_to_tuple(await con.fetchval(query, match_id))


async def get_scoreboard(con: Connection, match_id: str):

    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )

    query = """
    SELECT
        json_build_object(
            'gt_short',    g.gametype_short,
            'gt',          g.gametype_name,
            'factory',     f.factory_short,
            'map',         mm.map_name,
            'team1_score', m.team1_score,
            'team2_score', m.team2_score,
            'timestamp',   m.timestamp,
            'datetime',    TO_CHAR(to_timestamp(m.timestamp), '{DATETIME_FORMAT}'),
            'duration',    TO_CHAR((m.duration || ' second')::interval, 'MI:SS')
        )
    FROM
        matches m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN factories f ON f.factory_id = m.factory_id
    LEFT JOIN maps mm ON m.map_id = mm.map_id
    WHERE
        m.match_id = $1;
    """.format(
        DATETIME_FORMAT=DATETIME_FORMAT
    )
    summary = await con.fetchval(query, match_id)
    if summary is None:
        raise MatchNotFound(match_id)

    query = """
    SELECT sum(rating) as diff
    FROM (
        SELECT team, avg({RATING_COLUMN})*(case when team = 1 then 1 else -1 end) as rating
        FROM scoreboards
        WHERE match_perf is not NULL AND match_id = $1
        GROUP BY team
    ) t

    """.format(
        RATING_COLUMN="old_r2_value"
        if USE_AVG_PERF[summary["gt_short"]]
        else "old_r1_mean"
    )
    summary["rating_diff"] = await con.fetchval(query, match_id)
    if summary["rating_diff"] is not None:
        summary["rating_diff"] = round(summary["rating_diff"], 2)

    query = """
    SELECT
        json_object_agg(t.steam_id, t.weapon_stats)
    FROM (
        SELECT
            t.steam_id::text,
            json_object_agg(t.weapon_short, ARRAY[t.frags, t.hits, t.shots, t.damage_dealt, t.damage_taken]) AS weapon_stats
        FROM (
            SELECT
                w.weapon_short,
                SUM(sw.frags) AS frags,
                SUM(sw.hits) AS hits,
                SUM(sw.shots) AS shots,
                SUM(sw.damage_dealt) AS damage_dealt,
                SUM(sw.damage_taken) AS damage_taken,
                s.steam_id
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

    if USE_AVG_PERF[summary["gt_short"]]:
        rating_columns = """
            'old',   CAST( ROUND( CAST(t.old_r2_value AS NUMERIC), 2) AS REAL ),
            'new',   CAST( ROUND( CAST(t.new_r2_value AS NUMERIC), 2) AS REAL ),
            'old_d', 0,
            'new_d', 0
        """
    else:
        rating_columns = """
            'old',   CAST( ROUND( CAST(t.old_r1_mean      AS NUMERIC), 2) AS REAL ),
            'old_d', CAST( ROUND( CAST(t.old_r1_deviation AS NUMERIC), 2) AS REAL ),
            'new',   CAST( ROUND( CAST(t.new_r1_mean      AS NUMERIC), 2) AS REAL ),
            'new_d', CAST( ROUND( CAST(t.new_r1_deviation AS NUMERIC), 2) AS REAL )
        """

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
                    'score',        t.score,
                    'frags',        t.frags,
                    'deaths',       t.deaths,
                    'damage_dealt', t.damage_dealt,
                    'damage_taken', t.damage_taken,
                    'alive_time',   t.alive_time
                ),
                'rating', json_build_object({RATING_COLUMNS}),
                'medal_stats', ms.medal_stats,
                'weapon_stats', ws.weapon_stats
            ) AS item
        FROM
            scoreboards t
        LEFT JOIN players p ON p.steam_id = t.steam_id
        LEFT JOIN (
            SELECT
                t.steam_id, t.team,
                json_object_agg(t.weapon_short, ARRAY[t.frags, t.hits, t.shots, t.accuracy, t.damage_dealt, t.damage_dealt_percent]) AS weapon_stats
            FROM
                (
                SELECT
                    s.steam_id, s.team, w.weapon_short, sw.frags, sw.hits, sw.shots,
                    sw.damage_dealt,
                    CASE WHEN s.damage_dealt = 0 THEN 0
                        ELSE 100. * sw.damage_dealt / s.damage_dealt
                    END AS damage_dealt_percent,
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
        ORDER BY t.score DESC, t.steam_id ASC
    ) t
    """.format(
        RATING_COLUMNS=rating_columns
    )
    overall_stats = await con.fetchval(query, match_id)

    medals_available = await get_medals_available(con, match_id)

    query = """
    SELECT
        array_agg(w.weapon_short ORDER BY w.weapon_id ASC)
    FROM (
        SELECT DISTINCT weapon_id
        FROM scoreboards_weapons
        WHERE match_id = $1
    ) sw
    LEFT JOIN weapons w ON w.weapon_id = sw.weapon_id
    """
    weapons_available = await con.fetchval(query, match_id)

    rules = GAMETYPE_RULES[summary["gt_short"]]
    return {
        "summary": summary,
        "player_stats": {"weapons": player_weapon_stats, "medals": player_medal_stats},
        "team_stats": {"overall": overall_stats},
        "weapons_available": weapons_available,
        "medals_available": medals_available,
        "medals_in_scoreboard_mid": rules.medals_in_scoreboard_mid(),
        "medals_in_scoreboard_right": rules.medals_in_scoreboard_right(),
    }
