# -*- coding: utf-8 -*-
#

import re
from functools import reduce
from datetime import datetime
from common import clean_name, log_exception, DATETIME_FORMAT
from conf import settings as cfg
from db import db_connect, cache
from math import ceil

GAMETYPE_IDS = cache.GAMETYPE_IDS
LAST_GAME_TIMESTAMPS = cache.LAST_GAME_TIMESTAMPS
GAMETYPE_NAMES = cache.GAMETYPE_NAMES

KEEPING_TIME = 60*60*24*30
MATCH_LIST_ITEM_COUNT = 25
MOVING_AVG_COUNT = cfg['moving_average_count']

SQL_TOP_PLAYERS_BY_GAMETYPE = '''
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
'''.format( MATCH_LIST_ITEM_COUNT )

def get_list(gametype, page, show_inactive = False):

  try:
    gametype_id = GAMETYPE_IDS[ gametype ];
  except KeyError:
    return {
      "ok": False,
      "message": "gametype is not supported: " + gametype
    }

  try:
    db = db_connect()
    cu = db.cursor()
    query = SQL_TOP_PLAYERS_BY_GAMETYPE + '''
    LIMIT %(limit)s
    OFFSET %(offset)s'''
    cu.execute(query, {
      'gametype_id': gametype_id,
      'start_timestamp': LAST_GAME_TIMESTAMPS[ gametype_id ]-KEEPING_TIME if show_inactive is False else 0,
      'limit': cfg["player_count_per_page"],
      'offset': cfg["player_count_per_page"]*page
    })

    result = []
    player_count = 0
    for row in cu.fetchall():
      if row[0] != None:
        result.append({
          "_id": str(row[0]),
          "name": row[1],
          "model": (row[2] + ("/default" if row[2].find("/") == -1 else "")).lower(),
          "rating": round(row[3], 2),
          "rd": round(row[4], 2),
          "n": row[5],
          "rank": row[7]
        })
      player_count = row[6]

    steam_ids = list( map(
      lambda player: player['_id'],
      result
    ) )
    cu.execute('''SELECT
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
    ''', [gametype_id, tuple(steam_ids)])

    for row in cu.fetchall():
      try:
        result_index = steam_ids.index( str(row[0]) )
        result[ result_index ][ "win_ratio" ] = int(row[1])
      except ValueError:
        pass # must not happen

    result = {
      "ok": True,
      "response": result,
      "page_count": ceil(player_count / cfg["player_count_per_page"])
    }
  except Exception as e:
    db.rollback()
    log_exception(e)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
  finally:
    cu.close()
    db.close()

  return result


def generate_user_ratings(gametype, formula):
  tokens = re.findall("[a-z]+", formula)
  valid_tokens = ["s", "k", "d", "dg", "dd", "dt", "mc", "ma", "md", "t", "w"]

  try:
    gametype_id = GAMETYPE_IDS[ gametype ];
  except KeyError:
    return {
      "ok": False,
      "message": "gametype is not supported: " + gametype
    }

  invalid_tokens = list( filter( lambda item: item not in valid_tokens and item.isnumeric() == False, tokens ) )
  if len(invalid_tokens) > 0:
    return {
      "ok": False,
      "message": "invalid tokens " + ", ".join( invalid_tokens )
    }

  try:
    db = db_connect()
    cu = db.cursor()

    rows = cu.execute('''
SELECT
  steam_id,
  COUNT(steam_id),
  AVG( ''' + formula + ''' ) as rating,
  MIN(name)
FROM (
  SELECT
    m.match_id,
    s.steam_id,
    p.name,
    s.team,
    s.score AS s,
    s.frags AS k,
    s.deaths AS d,
    s.damage_dealt AS dg,
    s.damage_dealt AS dd,
    s.damage_taken AS dt,
    (select count from scoreboards_medals sm where sm.medal_id = 3 and s.steam_id = sm.steam_id and s.team = sm.team and s.match_id = sm.match_id ) as mc,
    (select count from scoreboards_medals sm where sm.medal_id = 2 and s.steam_id = sm.steam_id and s.team = sm.team and s.match_id = sm.match_id ) as ma,
    (select count from scoreboards_medals sm where sm.medal_id = 5 and s.steam_id = sm.steam_id and s.team = sm.team and s.match_id = sm.match_id ) as md,
    s.alive_time AS t,
    CASE
      WHEN s.team = 1 AND m.team1_score > m.team2_score THEN 1
      WHEN s.team = 2 AND m.team2_score > m.team1_score THEN 1
      ELSE 0
    END AS w,
    m.timestamp, rank() over (partition by s.steam_id order by m.timestamp desc) as rank
  FROM matches m
  LEFT JOIN scoreboards s on s.match_id = m.match_id
  LEFT JOIN players p ON p.steam_id = s.steam_id
  WHERE m.gametype_id = %s and s.match_perf IS NOT NULL order by m.timestamp desc
) t WHERE rank <= %s GROUP BY steam_id HAVING MAX(rank) > 10 ORDER by rating DESC;
  ''', [gametype_id, MOVING_AVG_COUNT])

    result = []
    for row in cu.fetchall():
      result.append({
        "_id": row[0],
        "n": row[1],
        "rating": float(round(row[2], 2)),
        "name": clean_name(row[3])
      })

    result = {
      "ok": True,
      "message": result
    }
  except Exception as e:
    db.rollback()
    log_exception(e)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
  finally:
    cu.close()
    db.close()

  return result


def export(gametype):

  try:
    gametype_id = GAMETYPE_IDS[ gametype ];
  except KeyError:
    return {
      "ok": False,
      "message": "gametype is not supported: " + gametype
    }

  try:
    db = db_connect()
  except Exception as e:
    log_exception(e)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
    return result

  try:
    cu = db.cursor()
    query = '''
    SELECT
      p.steam_id, p.name, gr.mean, gr.n
    FROM
      players p
    LEFT JOIN gametype_ratings gr ON
      gr.steam_id = p.steam_id
    WHERE
      gr.gametype_id = %s
    ORDER BY gr.mean DESC
    '''
    cu.execute(query, [gametype_id])

    result = []
    for row in cu.fetchall():
      if row[0] != None:
        result.append({
          "_id": str(row[0]),
          "name": clean_name(row[1]),
          "rating": row[2],
          "n": row[3]
        })

    result = {
      "ok": True,
      "response": result
    }
  except Exception as e:
    db.rollback()
    log_exception(e)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
  finally:
    cu.close()
    db.close()

  return result


def get_player_info_old(steam_id):

  try:
    db = db_connect()
    cu = db.cursor()
    result = {}
    for gametype, gametype_id in GAMETYPE_IDS.items():
      query = '''
      SELECT
        p.steam_id, p.name, p.model, g.gametype_short, gr.mean, gr.n, m.match_id, m.timestamp, m.old_mean, rt.rank, rt.count
      FROM
        players p
      LEFT JOIN gametype_ratings gr ON gr.steam_id = p.steam_id
      LEFT JOIN gametypes g on gr.gametype_id = g.gametype_id
      LEFT JOIN (
        SELECT
          m.match_id, m.timestamp, m.gametype_id, s.old_mean
        FROM
          matches m
        LEFT JOIN scoreboards s ON s.match_id = m.match_id
        WHERE
          s.steam_id = %(steam_id)s AND
          m.gametype_id = %(gametype_id)s
        ORDER BY m.timestamp DESC
        LIMIT 50
      ) m ON m.gametype_id = g.gametype_id
      LEFT JOIN (''' + SQL_TOP_PLAYERS_BY_GAMETYPE + ''') rt ON rt.steam_id = p.steam_id
      WHERE
        p.steam_id = %(steam_id)s AND
        g.gametype_id = %(gametype_id)s
      ORDER BY m.timestamp ASC
      '''
      cu.execute(query, {'steam_id': steam_id, 'gametype_id': gametype_id, 'start_timestamp': LAST_GAME_TIMESTAMPS[ gametype_id ]-KEEPING_TIME})
      last_ratings = {}
      for row in cu.fetchall():
        result[ "_id" ] = str(row[0])
        result[ "name" ] = row[1]
        result[ "model" ] = row[2]
        rating = round(row[8], 2) if row[8] is not None else None

        if gametype not in last_ratings:
          last_ratings[ gametype ] = rating if rating is not None else 1

        if rating is None:
          rating = last_ratings[ gametype ]
        else:
          last_ratings[ gametype ] = rating

        if gametype not in result:
          result[ gametype ] = {"rating": round(row[4], 2) if row[4] is not None else 0, "n": row[5], "history": [], "rank": row[9], "max_rank": row[10]}
        result[ gametype ][ "history" ].append({"match_id": row[6], "timestamp": row[7], "rating": rating})

    result = {
      "ok": True,
      "player": result
    }
  except Exception as e:
    db.rollback()
    log_exception(e)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
  finally:
    cu.close()
    db.close()

  return result








def get_last_matches( gametype = None, steam_id = None, page = 0, from_ts = None, to_ts = None ):
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
    return {
      "ok": False,
      "message": "gametype is not accepted: " + gametype
    }

  title = "Recent games"

  try:
    db = db_connect()
    cu = db.cursor()

    where_clauses = []
    params        = {'offset': page * MATCH_LIST_ITEM_COUNT, 'limit': MATCH_LIST_ITEM_COUNT}
    if from_ts is not None:
      where_clauses.append("m.timestamp >= %(from_ts)s");
      params[ 'from_ts' ] = from_ts

    if to_ts is not None:
      where_clauses.append("m.timestamp <= %(to_ts)s");
      params[ 'to_ts' ] = to_ts

    if to_ts is not None or from_ts is not None:
      params['offset'] = 0
      params['limit'] = 1000 # TODO: fix this

    if gametype:
      where_clauses.append("m.gametype_id = %(gametype_id)s")
      title = "Recent {} games".format( GAMETYPE_NAMES[ gametype ] )
      params[ 'gametype_id' ] = GAMETYPE_IDS[ gametype ]

    if steam_id:
      cu.execute("SELECT name FROM players WHERE steam_id = %s", [ steam_id ])
      if cu.rowcount == 0:
        raise AssertionError("player not found in database")
      player_name = clean_name( cu.fetchone()[0] )
      title = "Recent games with {}".format( player_name ) + (" (" + GAMETYPE_NAMES[ gametype ] + ")" if gametype else "")
      where_clauses.append("m.match_id IN (SELECT match_id FROM scoreboards WHERE steam_id = %(steam_id)s)")
      params[ 'steam_id' ] = steam_id

    where_clause_str = "" if len(where_clauses) == 0 else "WHERE " + " AND ".join(where_clauses)

    query = '''
    SELECT
      count(m.match_id)
    FROM
      matches m
    {WHERE_CLAUSE}
    '''.replace("{WHERE_CLAUSE}\n", where_clause_str)

    cu.execute( query, params )
    overall_match_count = cu.fetchone()[0]

    query = '''
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
    '''.format(WHERE_CLAUSE = where_clause_str, DATETIME_FORMAT = DATETIME_FORMAT, NOTHING = "{}")

    cu.execute( query, params )
    matches = cu.fetchone()[0]

    result = {
      "ok": True,
      "page_count": ceil(overall_match_count / MATCH_LIST_ITEM_COUNT),
      "title": title,
      "matches": matches
    }

  except Exception as e:
    db.rollback()
    log_exception(e)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }

  cu.close()
  db.close()

  return result
