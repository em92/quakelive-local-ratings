from asyncpg import Connection

from qllr.common import clean_name


async def export(con: Connection, gametype_id: int):

    query = """
    SELECT
        p.steam_id, p.name, gr.mean, gr.n
    FROM
        players p
    LEFT JOIN gametype_ratings gr ON
        gr.steam_id = p.steam_id
    WHERE
        gr.gametype_id = $1
    ORDER BY gr.mean DESC
    """

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

    return {"ok": True, "response": result}
