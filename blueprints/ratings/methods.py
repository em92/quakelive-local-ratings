from db import cache, db_connect
from conf import settings as cfg
from common import MATCH_LIST_ITEM_COUNT
from exceptions import InvalidGametype
from math import ceil

KEEPING_TIME = 60 * 60 * 24 * 30

GAMETYPE_IDS = cache.GAMETYPE_IDS
MOVING_AVG_COUNT = cfg["moving_average_count"]
LAST_GAME_TIMESTAMPS = cache.LAST_GAME_TIMESTAMPS

SQL_TOP_PLAYERS_BY_GAMETYPE = """
  SELECT
    p.steam_id, p.name, p.model, gr.mean AS rating, gr.deviation, gr.n, count(*) OVER () AS count, ROW_NUMBER() OVER (ORDER BY gr.mean DESC) AS rank
  FROM
    players p
  LEFT JOIN gametype_ratings gr ON
    gr.steam_id = p.steam_id
  WHERE
    gr.n >= 10 AND
    gr.last_played_timestamp > LEAST( %(start_timestamp)s, (SELECT timestamp FROM matches WHERE gametype_id = %(gametype_id)s ORDER BY timestamp DESC LIMIT 1 OFFSET {} ) ) AND
    gr.gametype_id = %(gametype_id)s
  ORDER BY gr.mean DESC
""".format(
    MATCH_LIST_ITEM_COUNT
)


async def get_list(gametype: str, page: int, show_inactive=False):

    try:
        gametype_id = GAMETYPE_IDS[gametype]
    except KeyError:
        raise InvalidGametype(gametype)

    try:
        db = db_connect()
        cu = db.cursor()
        query = (
            SQL_TOP_PLAYERS_BY_GAMETYPE
            + """
    LIMIT %(limit)s
    OFFSET %(offset)s"""
        )
        cu.execute(
            query,
            {
                "gametype_id": gametype_id,
                "start_timestamp": LAST_GAME_TIMESTAMPS[gametype_id] - KEEPING_TIME
                if show_inactive is False
                else 0,
                "limit": cfg["player_count_per_page"],
                "offset": cfg["player_count_per_page"] * page,
            },
        )

        result = []
        player_count = 0
        for row in cu.fetchall():
            if row[0] != None:
                result.append(
                    {
                        "_id": str(row[0]),
                        "name": row[1],
                        "model": (
                            row[2] + ("/default" if row[2].find("/") == -1 else "")
                        ).lower(),
                        "rating": round(row[3], 2),
                        "rd": round(row[4], 2),
                        "n": row[5],
                        "rank": row[7],
                    }
                )
            player_count = row[6]

        steam_ids = list(map(lambda player: player["_id"], result))
        cu.execute(
            """SELECT
        s.steam_id,
        CEIL(AVG(CASE
          WHEN m.team1_score > m.team2_score AND s.team = 1 THEN 1
          WHEN m.team2_score > m.team1_score AND s.team = 2 THEN 1
          ELSE 0
        END)*100)
      FROM
        matches m
      LEFT JOIN scoreboards s ON s.match_id = m.match_id
      WHERE
        m.gametype_id = %s AND s.steam_id IN %s
      GROUP BY s.steam_id;
    """,
            [gametype_id, tuple(steam_ids)],
        )

        for row in cu.fetchall():
            try:
                result_index = steam_ids.index(str(row[0]))
                result[result_index]["win_ratio"] = int(row[1])
            except ValueError:
                pass  # must not happen

        result = {
            "ok": True,
            "response": result,
            "page_count": ceil(player_count / cfg["player_count_per_page"]),
        }
    except Exception as e:
        db.rollback()
        result = {"ok": False, "message": type(e).__name__ + ": " + str(e)}
    finally:
        cu.close()
        db.close()

    return result
