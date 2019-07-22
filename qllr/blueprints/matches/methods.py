import json
from math import ceil

from asyncpg import Connection

from qllr.common import DATETIME_FORMAT, clean_name
from qllr.db import cache
from qllr.exceptions import InvalidGametype, PlayerNotFound

MATCH_LIST_ITEM_COUNT = 25


async def get_last_matches(
    con: Connection, gametype=None, steam_id=None, page=0, from_ts=None, to_ts=None
):
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
    if gametype != None and gametype not in cache.GAMETYPE_IDS:
        raise InvalidGametype(gametype)

    title = "Recent games"

    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )

    where_clauses = []
    params = []
    offset = page * MATCH_LIST_ITEM_COUNT
    limit = MATCH_LIST_ITEM_COUNT

    if from_ts is not None:
        params.append(from_ts)
        where_clauses.append("m.timestamp >= ${}".format(len(params)))

    if to_ts is not None:
        params.append(to_ts)
        where_clauses.append("m.timestamp <= ${}".format(len(params)))

    if to_ts is not None or from_ts is not None:
        offset = 0
        limit = 1000  # TODO: fix this

    if gametype:
        params.append(cache.GAMETYPE_IDS[gametype])
        where_clauses.append("m.gametype_id = ${}".format(len(params)))
        title = "Recent {} games".format(cache.GAMETYPE_NAMES[gametype])

    if steam_id:
        row = await con.fetchval(
            "SELECT name FROM players WHERE steam_id = $1", steam_id
        )
        if row is None:
            raise PlayerNotFound(steam_id)

        player_name = clean_name(row)
        title = "Recent games with {}".format(player_name) + (
            " (" + cache.GAMETYPE_NAMES[gametype] + ")" if gametype else ""
        )
        params.append(steam_id)
        where_clauses.append(
            "m.match_id IN (SELECT match_id FROM scoreboards WHERE steam_id = ${})".format(
                len(params)
            )
        )

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

    row = await con.fetchval(query, *params)
    overall_match_count = row

    # we assume, that offset and limit are ALWAYS integers
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
        OFFSET {OFFSET}
        LIMIT {LIMIT}
    ) m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN maps mm ON mm.map_id = m.map_id
    """.format(
        WHERE_CLAUSE=where_clause_str,
        DATETIME_FORMAT=DATETIME_FORMAT,
        NOTHING="{}",
        OFFSET=int(offset),
        LIMIT=int(limit),
    )

    row = await con.fetchval(query, *params)
    matches = row

    return {
        "ok": True,
        "page_count": ceil(overall_match_count / MATCH_LIST_ITEM_COUNT),
        "title": title,
        "matches": matches,
    }
