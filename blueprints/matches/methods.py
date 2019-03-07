from db import db_connect, cache, get_db_pool
from common import DATETIME_FORMAT, clean_name
from math import ceil
from collections import OrderedDict
import json
from exceptions import InvalidGametype, PlayerNotFound

GAMETYPE_IDS = cache.GAMETYPE_IDS
GAMETYPE_NAMES = cache.GAMETYPE_NAMES
MATCH_LIST_ITEM_COUNT = 25


async def get_last_matches(gametype=None, steam_id=None, page=0, from_ts=None, to_ts=None):
    """
    Returns last matches

    Returns: {
        "ok: True/False - on success/fail
        "matches": [
            {
                "match_id": ...
                "timestamp": ...
                "gametype" ...
                "map": ...
            },
            {...}
        ]
    }
    """
    if gametype != None and gametype not in GAMETYPE_IDS:
        raise InvalidGametype(gametype)

    title = "Recent games"

    dbpool = await get_db_pool()
    con = await dbpool.acquire()
    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )
    tr = con.transaction()
    await tr.start()

    try:
        where_clauses = []
        params = OrderedDict()
        params["offset"] = page * MATCH_LIST_ITEM_COUNT
        params["limit"] = MATCH_LIST_ITEM_COUNT
        params["from_ts"] = None
        params["to_ts"] = None
        params["gametype_id"] = None
        params["steam_id"] = None

        if from_ts is not None:
            where_clauses.append("m.timestamp >= $3")
            params["from_ts"] = from_ts

        if to_ts is not None:
            where_clauses.append("m.timestamp <= $4")
            params["to_ts"] = to_ts

        if to_ts is not None or from_ts is not None:
            params["offset"] = 0
            params["limit"] = 1000  # TODO: fix this

        if gametype:
            where_clauses.append("m.gametype_id = $5")
            title = "Recent {} games".format(GAMETYPE_NAMES[gametype])
            params["gametype_id"] = GAMETYPE_IDS[gametype]

        if steam_id:
            row = await con.fetchval("SELECT name FROM players WHERE steam_id = $1", steam_id)
            if row is None:
                raise PlayerNotFound(steam_id)

            player_name = clean_name(row[0])
            title = "Recent games with {}".format(player_name) + (
                " (" + GAMETYPE_NAMES[gametype] + ")" if gametype else ""
            )
            where_clauses.append(
                "m.match_id IN (SELECT match_id FROM scoreboards WHERE steam_id = $6)"
            )
            params["steam_id"] = steam_id

        where_clause_str = (
            "" if len(where_clauses) == 0 else "WHERE " + " AND ".join(where_clauses)
        )

        # TODO: вынести эту функцию в кэш
        query = """
        SELECT
            count(m.match_id)
        FROM
            matches m
        {WHERE_CLAUSE}
        """.replace(
            "{WHERE_CLAUSE}\n", where_clause_str
        )

        row = await con.fetchval(query, *params.values())
        overall_match_count = row[0]

        query = """
        SELECT
            COALESCE(array_agg(json_build_object(
                'match_id', m.match_id,
                'datetime', to_char(to_timestamp(timestamp), '{DATETIME_FORMAT}'),
                'timestamp', timestamp,
                'gametype', g.gametype_short,
                'team1_score', m.team1_score,
                'team2_score', m.team2_score,
                'map', mm.map_name
            ) ORDER BY timestamp DESC), '{NOTHING}')
        FROM (
            SELECT *
            FROM matches m
            {WHERE_CLAUSE}
            ORDER BY timestamp DESC
            OFFSET $1
            LIMIT $2
        ) m
        LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
        LEFT JOIN maps mm ON mm.map_id = m.map_id
        """.format(
            WHERE_CLAUSE=where_clause_str, DATETIME_FORMAT=DATETIME_FORMAT, NOTHING="{}"
        )

        row = await con.fetchval(query, *params.values())
        matches = row[0]

        result = {
            "ok": True,
            "page_count": ceil(overall_match_count / MATCH_LIST_ITEM_COUNT),
            "title": title,
            "matches": matches,
        }

    finally:
        await tr.rollback()
        await dbpool.release(con)

    return result
