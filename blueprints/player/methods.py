from common import DATETIME_FORMAT, clean_name, log_exception
from db import db_connect
from functools import reduce
from conf import settings

MOVING_AVG_COUNT = settings["moving_average_count"]


async def get_player_info(steam_id):

    result = {}

    try:
        db = db_connect()
        cu = db.cursor()

        # player name, rating and games played
        cu.execute(
            """
      SELECT p.name, COALESCE(t.ratings, '{ }') AS ratings
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
        WHERE gr.steam_id = %(steam_id)s
        GROUP BY gr.steam_id
      ) t ON p.steam_id = t.steam_id
      WHERE p.steam_id = %(steam_id)s
    """,
            {"steam_id": steam_id},
        )

        if cu.rowcount == 0:
            raise AssertionError("player not found in database")

        row = cu.fetchall()[0]
        result = {"name": row[0], "ratings": row[1]}

        # weapon stats (frags + acc)
        cu.execute(
            """
      SELECT json_build_object('name', w.weapon_name, 'short', w.weapon_short, 'frags', t2.frags, 'acc', t.accuracy)
      FROM (
        SELECT
          weapon_id,
          CASE WHEN SUM(shots) = 0 THEN 0
            ELSE CAST(100. * SUM(hits) / SUM(shots) AS INT)
          END AS accuracy
        FROM (SELECT weapon_id, frags, hits, shots FROM scoreboards_weapons sw LEFT JOIN matches m ON m.match_id = sw.match_id WHERE sw.steam_id = %(steam_id)s ORDER BY timestamp DESC LIMIT %(MOVING_AVG_COUNT)s) sw
        GROUP BY weapon_id
      ) t
      LEFT JOIN weapons w ON t.weapon_id = w.weapon_id
      LEFT JOIN (
        SELECT
          weapon_id,
          SUM(frags) AS frags
        FROM scoreboards_weapons sw
        WHERE steam_id = %(steam_id)s
        GROUP BY weapon_id
      ) t2 ON t2.weapon_id = t.weapon_id
      ORDER BY t.weapon_id ASC
    """,
            {"MOVING_AVG_COUNT": MOVING_AVG_COUNT, "steam_id": steam_id},
        )

        result["weapon_stats"] = list(map(lambda row: row[0], cu.fetchall()))

        # fav map
        cu.execute(
            """
      SELECT map_name
      FROM (
        SELECT map_id, COUNT(*) AS n
        FROM matches m
        WHERE match_id IN (SELECT match_id FROM scoreboards WHERE steam_id = %(steam_id)s)
        GROUP BY map_id
      ) t
      LEFT JOIN maps ON maps.map_id = t.map_id
      ORDER BY n DESC
      LIMIT 1
    """,
            {"steam_id": steam_id},
        )

        if cu.rowcount == 0:
            fav_map = "None"
        else:
            fav_map = cu.fetchone()[0]

        result["fav"] = {
            "map": fav_map,
            "gt": "None"
            if len(result["ratings"]) == 0
            else result["ratings"][0]["gametype"],
            "wpn": reduce(
                lambda sum, x: sum if sum["frags"] > x["frags"] else x,
                result["weapon_stats"],
                {"frags": 0, "name": "None"},
            )["name"],
        }

        # 10 last matches
        cu.execute(
            """
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
      WHERE s.steam_id = %(steam_id)s
      ORDER BY timestamp DESC
      LIMIT 10
    ) m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN maps mm ON mm.map_id = m.map_id
    """.format(
                DATETIME_FORMAT=DATETIME_FORMAT
            ),
            {"steam_id": steam_id},
        )

        result["matches"] = cu.fetchone()[0]

        result = {"response": result, "title": clean_name(result["name"]), "ok": True}

    except AssertionError as e:
        result = {"ok": False, "message": str(e)}
    except Exception as e:
        db.rollback()
        log_exception(e)
        result = {"ok": False, "message": type(e).__name__ + ": " + str(e)}
    finally:
        cu.close()
        db.close()

    return result
