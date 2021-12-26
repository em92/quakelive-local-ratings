from asyncpg import Connection

from qllr.db import cache, rating_column

from ..ratings.methods import KEEPING_TIME, get_sql_top_players_query_by_gametype_id


async def get_player_info_old(con: Connection, steam_id: int):

    result = {}
    for gametype, gametype_id in cache.GAMETYPE_IDS.items():
        query = """
        SELECT
            p.steam_id,
            p.name,
            p.model,
            g.gametype_short,
            gr.{RATING_COLUMN},
            gr.n,
            m.match_id::text,
            m.timestamp,
            m.old_{RATING_COLUMN},
            rt.rank,
            rt.count
        FROM
            players p
        LEFT JOIN gametype_ratings gr ON gr.steam_id = p.steam_id
        LEFT JOIN gametypes g on gr.gametype_id = g.gametype_id
        LEFT JOIN (
            SELECT
                m.match_id,
                m.timestamp,
                m.gametype_id,
                s.old_{RATING_COLUMN}
            FROM
                matches m
            LEFT JOIN scoreboards s ON s.match_id = m.match_id
            WHERE
                s.steam_id = $3 AND
                m.gametype_id = $2
            ORDER BY m.timestamp DESC
            LIMIT 50
        ) m ON m.gametype_id = g.gametype_id
        LEFT JOIN ({SQL_TOP_PLAYERS_BY_GAMETYPE}) rt ON rt.steam_id = p.steam_id
        WHERE
            p.steam_id = $3 AND
            g.gametype_id = $2
        ORDER BY m.timestamp ASC
        """.format(
            RATING_COLUMN=rating_column(gametype_id),
            SQL_TOP_PLAYERS_BY_GAMETYPE=get_sql_top_players_query_by_gametype_id(
                gametype_id
            ),
        )

        last_ratings = {}
        async for row in con.cursor(
            query,
            cache.LAST_GAME_TIMESTAMPS[gametype_id] - KEEPING_TIME,
            gametype_id,
            steam_id,
        ):
            result["_id"] = str(row[0])
            result["name"] = row[1]
            result["model"] = row[2]
            rating = round(row[8], 2) if row[8] is not None else None

            if gametype not in last_ratings:
                last_ratings[gametype] = rating if rating is not None else 1

            if rating is None:
                rating = last_ratings[gametype]
            else:
                last_ratings[gametype] = rating

            if gametype not in result:
                result[gametype] = {
                    "rating": round(row[4], 2) if row[4] is not None else 0,
                    "n": row[5],
                    "history": [],
                    "rank": row[9],
                    "max_rank": row[10],
                }
            result[gametype]["history"].append(
                {"match_id": row[6], "timestamp": row[7], "rating": rating}
            )

    return {"player": result}
