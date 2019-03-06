from db import db_connect, cache
from common import DATETIME_FORMAT, clean_name
from math import ceil

GAMETYPE_IDS = cache.GAMETYPE_IDS
GAMETYPE_NAMES = cache.GAMETYPE_NAMES
MATCH_LIST_ITEM_COUNT = 25


def get_last_matches(gametype=None, steam_id=None, page=0, from_ts=None, to_ts=None):
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
        return {"ok": False, "message": "gametype is not accepted: " + gametype}

    title = "Recent games"

    try:
        db = db_connect()
        cu = db.cursor()

        where_clauses = []
        params = {
            "offset": page * MATCH_LIST_ITEM_COUNT,
            "limit": MATCH_LIST_ITEM_COUNT,
        }
        if from_ts is not None:
            where_clauses.append("m.timestamp >= %(from_ts)s")
            params["from_ts"] = from_ts

        if to_ts is not None:
            where_clauses.append("m.timestamp <= %(to_ts)s")
            params["to_ts"] = to_ts

        if to_ts is not None or from_ts is not None:
            params["offset"] = 0
            params["limit"] = 1000  # TODO: fix this

        if gametype:
            where_clauses.append("m.gametype_id = %(gametype_id)s")
            title = "Recent {} games".format(GAMETYPE_NAMES[gametype])
            params["gametype_id"] = GAMETYPE_IDS[gametype]

        if steam_id:
            cu.execute("SELECT name FROM players WHERE steam_id = %s", [steam_id])
            if cu.rowcount == 0:
                raise AssertionError("player not found in database")
            player_name = clean_name(cu.fetchone()[0])
            title = "Recent games with {}".format(player_name) + (
                " (" + GAMETYPE_NAMES[gametype] + ")" if gametype else ""
            )
            where_clauses.append(
                "m.match_id IN (SELECT match_id FROM scoreboards WHERE steam_id = %(steam_id)s)"
            )
            params["steam_id"] = steam_id

        where_clause_str = (
            "" if len(where_clauses) == 0 else "WHERE " + " AND ".join(where_clauses)
        )

        query = """
    SELECT
      count(m.match_id)
    FROM
      matches m
    {WHERE_CLAUSE}
    """.replace(
            "{WHERE_CLAUSE}\n", where_clause_str
        )

        cu.execute(query, params)
        overall_match_count = cu.fetchone()[0]

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
      OFFSET %(offset)s
      LIMIT %(limit)s
    ) m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN maps mm ON mm.map_id = m.map_id
    """.format(
            WHERE_CLAUSE=where_clause_str, DATETIME_FORMAT=DATETIME_FORMAT, NOTHING="{}"
        )

        cu.execute(query, params)
        matches = cu.fetchone()[0]

        result = {
            "ok": True,
            "page_count": ceil(overall_match_count / MATCH_LIST_ITEM_COUNT),
            "title": title,
            "matches": matches,
        }

    except Exception as e:
        db.rollback()
        result = {"ok": False, "message": type(e).__name__ + ": " + str(e)}

    cu.close()
    db.close()

    return result
