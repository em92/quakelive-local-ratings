import json
from math import ceil

from asyncpg import Connection

from qllr.common import MATCH_LIST_ITEM_COUNT
from qllr.db import cache
from qllr.settings import PLAYER_COUNT_PER_PAGE

KEEPING_TIME = 60 * 60 * 24 * 30

SQL_TOP_PLAYERS_BY_GAMETYPE = """
    SELECT
        p.steam_id,
        p.name,
        p.model,
        gr.rating,
        gr.deviation,
        gr.n,
        count(*) OVER () AS count,
        ROW_NUMBER() OVER (ORDER BY gr.rating DESC) AS rank
    FROM
        players p
    LEFT JOIN (SUBQUERY) gr ON
        gr.steam_id = p.steam_id
    WHERE
        gr.n >= 10 AND
        gr.last_played_timestamp > LEAST( $1, (
            SELECT timestamp
            FROM matches
            WHERE gametype_id = $2
            ORDER BY timestamp DESC
            LIMIT 1 OFFSET {OFFSET}
        )) AND
        gr.gametype_id = $2
    ORDER BY gr.rating DESC
""".format(
    OFFSET=int(MATCH_LIST_ITEM_COUNT)
).replace(
    "(SUBQUERY)", "({SUBQUERY})"
)

SQL_TOP_PLAYERS_BY_GAMETYPE_R1 = SQL_TOP_PLAYERS_BY_GAMETYPE.format(
    SUBQUERY="""
    SELECT
        steam_id,
        r1_mean AS rating,
        r1_deviation AS deviation,
        last_played_timestamp,
        gametype_id,
        n
    FROM
         gametype_ratings
    """
)

SQL_TOP_PLAYERS_BY_GAMETYPE_R2 = SQL_TOP_PLAYERS_BY_GAMETYPE.format(
    SUBQUERY="""
    SELECT
        steam_id,
        r2_value AS rating,
        0 AS deviation,
        last_played_timestamp,
        gametype_id,
        n
    FROM
         gametype_ratings
    """
)


def get_sql_top_players_query_by_gametype_id(gametype_id: int):
    if cache.USE_AVG_PERF[gametype_id]:
        return SQL_TOP_PLAYERS_BY_GAMETYPE_R2
    else:
        return SQL_TOP_PLAYERS_BY_GAMETYPE_R1


async def get_list(con: Connection, gametype_id: int, page: int, show_inactive=False):

    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )

    query = get_sql_top_players_query_by_gametype_id(
        gametype_id
    ) + "LIMIT {LIMIT} OFFSET {OFFSET}".format(
        LIMIT=int(PLAYER_COUNT_PER_PAGE), OFFSET=int(PLAYER_COUNT_PER_PAGE * page)
    )

    start_timestamp = 0
    if show_inactive is False:
        start_timestamp = cache.LAST_GAME_TIMESTAMPS[gametype_id] - KEEPING_TIME

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
        "response": result,
        "page_count": ceil(player_count / PLAYER_COUNT_PER_PAGE),
    }
