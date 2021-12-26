from asyncpg import Connection

from qllr.common import clean_name
from qllr.db import rating_column


async def export(con: Connection, gametype_id: int):

    query = """
    SELECT
        p.steam_id, p.name, {COLUMN}, gr.n
    FROM
        players p
    LEFT JOIN gametype_ratings gr ON
        gr.steam_id = p.steam_id
    WHERE
        gr.gametype_id = $1
    ORDER BY {COLUMN} DESC
    """.format(
        COLUMN=rating_column(gametype_id)
    )

    result = []
    async for row in con.cursor(query, gametype_id):
        result.append(
            {
                "_id": str(row[0]),
                "name": clean_name(row[1]),
                "rating": row[2],
                "n": row[3],
            }
        )

    return {"response": result}
