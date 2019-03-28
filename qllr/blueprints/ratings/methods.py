from qllr.db import cache
from qllr.common import MATCH_LIST_ITEM_COUNT
from qllr.settings import PLAYER_COUNT_PER_PAGE
from math import ceil
from asyncpg import Connection
import json

KEEPING_TIME = 60 * 60 * 24 * 30

LAST_GAME_TIMESTAMPS = cache.LAST_GAME_TIMESTAMPS

SQL_TOP_PLAYERS_BY_GAMETYPE = """
    SELECT
        p.steam_id,
        p.name,
        p.model,
        gr.mean AS rating,
        gr.deviation,
        gr.n,
        count(*) OVER () AS count,
        ROW_NUMBER() OVER (ORDER BY gr.mean DESC) AS rank
    FROM
        players p
    LEFT JOIN gametype_ratings gr ON
        gr.steam_id = p.steam_id
    WHERE
        gr.n >= 10 AND
        gr.last_played_timestamp > LEAST( $1, (
            SELECT timestamp
            FROM matches
            WHERE gametype_id = $2
            ORDER BY timestamp DESC
            LIMIT 1 OFFSET {}
        )) AND
        gr.gametype_id = $2
    ORDER BY gr.mean DESC
""".format(int(MATCH_LIST_ITEM_COUNT))


async def get_list(con: Connection, gametype_id: int, page: int, show_inactive=False):

    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )

    query = SQL_TOP_PLAYERS_BY_GAMETYPE + "LIMIT {LIMIT} OFFSET {OFFSET}".format(
        LIMIT=int(PLAYER_COUNT_PER_PAGE),
        OFFSET=int(PLAYER_COUNT_PER_PAGE * page)
    )

    start_timestamp = 0
    if show_inactive is False:
        start_timestamp = LAST_GAME_TIMESTAMPS[gametype_id] - KEEPING_TIME

    result = []
    player_count = 0
    async for row in con.cursor(query, start_timestamp, gametype_id):
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

    steam_ids = list(map(lambda player: int(player["_id"]), result))

    query = """
    SELECT
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
        m.gametype_id = $1 AND s.steam_id = ANY($2)
    GROUP BY s.steam_id;
    """

    for row in await con.fetch(query, gametype_id, steam_ids):
        try:
            result_index = steam_ids.index(row[0])
            result[result_index]["win_ratio"] = int(row[1])
        except ValueError:
            pass  # must not happen

    return {
        "ok": True,
        "response": result,
        "page_count": ceil(player_count / PLAYER_COUNT_PER_PAGE),
    }
