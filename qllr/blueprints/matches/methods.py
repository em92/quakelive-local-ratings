import json
from math import ceil

from asyncpg import Connection

from qllr.common import DATETIME_FORMAT, clean_name
from qllr.db import cache
from qllr.exceptions import InvalidGametype, PlayerNotFound

MATCH_LIST_ITEM_COUNT = 25


async def get_best_matches_of_player(con: Connection, steam_id: int, gametype: str):
    try:
        gametype_id = cache.GAMETYPE_IDS[gametype]
    except KeyError:
        raise InvalidGametype(gametype)

    await con.set_type_codec(
        "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )

    player_name = await _get_player_name(con, steam_id)

    params = [
        gametype_id,
        steam_id,
    ]

    where_clause_str = """
LEFT JOIN (
    SELECT subs.match_id, match_perf
    FROM scoreboards subs
    LEFT JOIN matches subm ON subs.match_id = subm.match_id
    WHERE subm.gametype_id = $1 AND
    steam_id = $2 AND
    match_perf IS NOT NULL AND
    alive_time >= 1200
    ORDER BY match_perf DESC
    LIMIT {LIMIT}
) s ON s.match_id = m.match_id
WHERE s.match_id IS NOT NULL
    """.format(
        LIMIT=MATCH_LIST_ITEM_COUNT
    )

    matches = await _get_matches(
        con,
        where_clause_str,
        params,
        "match_perf DESC",
        0,
        MATCH_LIST_ITEM_COUNT,
        "match_perf,",
    )

    return {
        "page_count": 0,
        "title": f"{player_name}'s best {cache.GAMETYPE_NAMES[gametype]} matches",
        "matches": matches,
    }


async def get_last_matches(
    con: Connection, gametype=None, steam_id=None, page=0, from_ts=None, to_ts=None
):
    """
    Returns last matches

    Returns: {
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
        player_name = await _get_player_name(con, steam_id)

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

    # TODO: correctness of cached overall_match_count is not covered by tests
    cache_key = "{}_{}".format(
        __name__, cache.key(where_clause_str + "_" + str(params), gametype)
    )
    if cache.store.get(cache_key) is not None:
        overall_match_count = cache.store.get(cache_key)
    else:
        query = """
        SELECT
            count(m.match_id)
        FROM
            matches m
        {WHERE_CLAUSE}
        """.replace(
            "{WHERE_CLAUSE}\n", where_clause_str
        )

        overall_match_count = await con.fetchval(query, *params)
        cache.store[cache_key] = overall_match_count

    matches = await _get_matches(
        con, where_clause_str, params, "timestamp DESC", offset, limit
    )

    return {
        "page_count": ceil(overall_match_count / MATCH_LIST_ITEM_COUNT),
        "title": title,
        "matches": matches,
    }


async def _get_player_name(con: Connection, steam_id: int):
    row = await con.fetchval("SELECT name FROM players WHERE steam_id = $1", steam_id)
    if row is None:
        raise PlayerNotFound(steam_id)

    return clean_name(row)


async def _get_matches(
    con: Connection,
    where_clause_str: str,
    params,
    order_by: str,
    offset: int,
    limit: int,
    extra_rows=None,
):
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
        ) ORDER BY {ORDER_BY}), '{NOTHING}')
    FROM (
        SELECT
            m.gametype_id,
            m.map_id,
            team1_score, team2_score,
            timestamp, {EXTRA_ROWS}
            m.match_id
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
        ORDER_BY=order_by,
        EXTRA_ROWS=extra_rows or "",
    )

    return await con.fetchval(query, *params)
