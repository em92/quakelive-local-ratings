# -*- coding: utf-8 -*-
#

import re
import sys
import traceback
import humanize
from functools import reduce
from datetime import datetime
from common import clean_name
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
    traceback.print_exc(file=sys.stderr)
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
    traceback.print_exc(file=sys.stderr)
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
    traceback.print_exc(file=sys.stderr)
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
    traceback.print_exc(file=sys.stderr)
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
    traceback.print_exc(file=sys.stderr)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
  finally:
    cu.close()
    db.close()

  return result


def get_player_info( steam_id ):

  result = {}

  try:
    db = db_connect()
    cu = db.cursor()

    # player name, rating and games played
    cu.execute('''
      SELECT p.name, COALESCE(t.ratings, '{ }') AS ratings
      FROM players p
      LEFT JOIN (
        SELECT gr.steam_id, array_agg( json_build_object(
          'rating', CAST( ROUND( CAST(gr.mean AS NUMERIC), 2) AS REAL ),
          'n', gr.n,
          'gametype_short', g.gametype_short,
          'gametype', g.gametype_name
        ) ORDER by gr.n DESC ) AS ratings
        FROM gametype_ratings gr
        LEFT JOIN gametypes g ON g.gametype_id = gr.gametype_id
        WHERE gr.steam_id = %(steam_id)s
        GROUP BY gr.steam_id
      ) t ON p.steam_id = t.steam_id
      WHERE p.steam_id = %(steam_id)s
    ''', {"steam_id": steam_id})

    if cu.rowcount == 0:
      raise AssertionError("player not found in database")

    row = cu.fetchall()[0]
    result = {
      "name": row[0],
      "ratings": row[1]
    }

    # weapon stats (frags + acc)
    cu.execute('''
      SELECT json_build_object('name', w.weapon_name, 'short', w.weapon_short, 'frags', t2.frags, 'acc', t.accuracy)
      FROM (
        SELECT
          weapon_id,
          CASE WHEN SUM(shots) = 0 THEN 0
            ELSE CAST(100. * SUM(hits) / SUM(shots) AS INT)
          END AS accuracy
        FROM (SELECT weapon_id, frags, hits, shots FROM scoreboards_weapons sw LEFT JOIN matches m ON m.match_id = sw.match_id WHERE sw.steam_id = %(steam_id)s ORDER BY timestamp DESC LIMIT %(MOVING_AVG_COUNT)s) sw
        GROUP BY weapon_id
      ) t
      LEFT JOIN weapons w ON t.weapon_id = w.weapon_id
      LEFT JOIN (
        SELECT
          weapon_id,
          SUM(frags) AS frags
        FROM scoreboards_weapons sw
        WHERE steam_id = %(steam_id)s
        GROUP BY weapon_id
      ) t2 ON t2.weapon_id = t.weapon_id
      ORDER BY t.weapon_id ASC
    ''', {"MOVING_AVG_COUNT": MOVING_AVG_COUNT, "steam_id": steam_id})

    result['weapon_stats'] = list( map( lambda row: row[0], cu.fetchall() ) )

    # fav map
    cu.execute('''
      SELECT map_name
      FROM (
        SELECT map_id, COUNT(*) AS n
        FROM matches m
        WHERE match_id IN (SELECT match_id FROM scoreboards WHERE steam_id = %(steam_id)s)
        GROUP BY map_id
      ) t
      LEFT JOIN maps ON maps.map_id = t.map_id
      ORDER BY n DESC
      LIMIT 1
    ''', {"steam_id": steam_id})

    if cu.rowcount == 0:
      fav_map = "None"
    else:
      fav_map = cu.fetchone()[0]

    result['fav'] = {
      "map": fav_map,
      "gt": "None" if len(result["ratings"]) == 0 else result["ratings"][0]["gametype"],
      "wpn": reduce(lambda sum, x: sum if sum['frags'] > x['frags'] else x, result['weapon_stats'], {"frags": 0, "name": "None"})["name"]
    }

    # 10 last matches
    cu.execute('''
    SELECT
      json_build_object(
        'match_id', m.match_id,
        'datetime', to_char(to_timestamp(timestamp), 'YYYY-MM-DD HH24:MI'),
        'timestamp', timestamp,
        'gametype', g.gametype_short,
        'result', CASE
          WHEN m.team1_score > m.team2_score AND s.team = 1 THEN 'Win'
          WHEN m.team1_score < m.team2_score AND s.team = 2 THEN 'Win'
          ELSE 'Loss'
        END,
        'team1_score', m.team1_score,
        'team2_score', m.team2_score,
        'map', mm.map_name
      )
    FROM
      (SELECT * FROM scoreboards WHERE steam_id = %(steam_id)s) s
    LEFT JOIN matches m ON s.match_id = m.match_id
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN maps mm ON mm.map_id = m.map_id
    ORDER BY timestamp DESC
    LIMIT 10
    ''', {"steam_id": steam_id})

    result["matches"] = []
    for row in cu:
      item = dict(row[0])
      item['timedelta'] = humanize.naturaltime( datetime.now() - datetime.fromtimestamp( item['timestamp'] ) )
      result["matches"].append( item )

    result = {
      "response": result,
      "title": clean_name( result['name'] ),
      "ok": True
    }

  except AssertionError as e:
    result = {
      "ok": False,
      "message": str(e)
    }
  except Exception as e:
    db.rollback()
    traceback.print_exc(file=sys.stderr)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
  finally:
    cu.close()
    db.close()

  return result


def get_scoreboard(match_id):

  try:
    db = db_connect()
    cu = db.cursor()

    query = '''
    SELECT
      json_build_object(
        'gt_short',    g.gametype_short,
        'gt',          g.gametype_name,
        'factory',     f.factory_short,
        'map',         mm.map_name,
        'team1_score', m.team1_score,
        'team2_score', m.team2_score,
        'rating_diff', CAST( ROUND( CAST(t.diff AS NUMERIC), 2) AS REAL ),
        'timestamp',   m.timestamp,
        'datetime',    TO_CHAR(to_timestamp(m.timestamp), 'YYYY-MM-DD HH24:MI'),
        'duration',    TO_CHAR((m.duration || ' second')::interval, 'MI:SS')
      )
    FROM
      matches m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN factories f ON f.factory_id = m.factory_id
    LEFT JOIN maps mm ON m.map_id = mm.map_id
    LEFT JOIN (
      SELECT match_id, sum(rating) as diff
      FROM (
        SELECT match_id, team, avg(old_mean)*(case when team = 1 then 1 else -1 end) as rating
        FROM scoreboards
        WHERE match_perf is not NULL AND match_id = %(match_id)s
        GROUP by match_id, team
      ) t
      GROUP by match_id
    ) t ON t.match_id = m.match_id
    WHERE
      m.match_id = %(match_id)s;
    '''
    cu.execute(query, {'match_id': match_id})
    try:
      summary = cu.fetchone()[0]
    except TypeError:
      return {
        "message": "match not found",
        "ok": False
      }

    query = '''
    SELECT
      json_object_agg(t.steam_id, t.weapon_stats)
    FROM (
      SELECT
        t.steam_id::text,
        json_object_agg(t.weapon_short, ARRAY[t.frags, t.hits, t.shots]) AS weapon_stats
      FROM (
        SELECT
          s.steam_id,
          w.weapon_short,
          SUM(sw.frags) AS frags,
          SUM(sw.hits) AS hits,
          SUM(sw.shots) AS shots
        FROM
          scoreboards s
        RIGHT JOIN scoreboards_weapons sw ON sw.match_id = s.match_id AND sw.steam_id = s.steam_id AND sw.team = s.team
        LEFT JOIN weapons w ON w.weapon_id = sw.weapon_id
        WHERE
          s.match_id = %s
        GROUP BY s.steam_id, w.weapon_short
      ) t
      GROUP BY t.steam_id
    ) t;
    '''
    cu.execute(query, [match_id])
    player_weapon_stats = cu.fetchone()[0]

    query = '''
    SELECT
      json_object_agg(t.steam_id, t.medal_stats)
    FROM (
      SELECT
        t.steam_id::text,
        json_object_agg(t.medal_short, t.count) AS medal_stats
      FROM (
        SELECT
          s.steam_id,
          m.medal_short,
          SUM(sm.count) AS count
        FROM
          scoreboards s
        RIGHT JOIN scoreboards_medals sm ON sm.match_id = s.match_id AND sm.steam_id = s.steam_id AND sm.team = s.team
        LEFT JOIN medals m ON m.medal_id = sm.medal_id
        WHERE
          s.match_id = %s
        GROUP BY s.steam_id, m.medal_short
      ) t
      GROUP BY t.steam_id
    ) t;
    '''
    cu.execute(query, [match_id])
    player_medal_stats = cu.fetchone()[0]

    query = '''
    SELECT
      array_agg(item)
    FROM (
      SELECT
        json_build_object(
          'steam_id', t.steam_id::text,
          'team', t.team::text,
          'name', p.name,
          'stats', json_build_object(
            'score',        t.score,
            'frags',        t.frags,
            'deaths',       t.deaths,
            'damage_dealt', t.damage_dealt,
            'damage_taken', t.damage_taken,
            'alive_time',   t.alive_time
          ),
          'rating', json_build_object(
            'old',   CAST( ROUND( CAST(t.old_mean      AS NUMERIC), 2) AS REAL ),
            'old_d', CAST( ROUND( CAST(t.old_deviation AS NUMERIC), 2) AS REAL ),
            'new',   CAST( ROUND( CAST(t.new_mean      AS NUMERIC), 2) AS REAL ),
            'new_d', CAST( ROUND( CAST(t.new_deviation AS NUMERIC), 2) AS REAL )
          ),
          'medal_stats', ms.medal_stats,
          'weapon_stats', ws.weapon_stats
        ) AS item
      FROM
        scoreboards t
      LEFT JOIN players p ON p.steam_id = t.steam_id
      LEFT JOIN (
        SELECT
          t.steam_id, t.team,
          json_object_agg(t.weapon_short, ARRAY[t.frags, t.hits, t.shots, t.accuracy]) AS weapon_stats
        FROM
          (
          SELECT
            s.steam_id, s.team, w.weapon_short, sw.frags, sw.hits, sw.shots,
            CASE WHEN sw.shots = 0 THEN 0
              ELSE CAST(100. * sw.hits / sw.shots AS INT)
            END AS accuracy
          FROM
            scoreboards s
          RIGHT JOIN scoreboards_weapons sw ON sw.match_id = s.match_id AND sw.steam_id = s.steam_id AND sw.team = s.team
          LEFT JOIN weapons w ON w.weapon_id = sw.weapon_id
          WHERE
            s.match_id = %(match_id)s
          ) t
          GROUP BY t.steam_id, t.team
      ) ws ON ws.steam_id = t.steam_id AND ws.team = t.team
      LEFT JOIN (
        SELECT
          t.steam_id, t.team,
          json_object_agg(t.medal_short, t.count) AS medal_stats
        FROM (
          SELECT
            s.steam_id, s.team, m.medal_short, sm.count
          FROM
            scoreboards s
          RIGHT JOIN scoreboards_medals sm ON sm.match_id = s.match_id AND sm.steam_id = s.steam_id AND sm.team = s.team
          LEFT JOIN medals m ON m.medal_id = sm.medal_id
          WHERE
            s.match_id = %(match_id)s
        ) t
        GROUP BY t.steam_id, t.team
      ) ms ON ms.steam_id = t.steam_id AND ms.team = t.team
      WHERE
        t.match_id = %(match_id)s
      ORDER BY t.score DESC
    ) t
    '''
    cu.execute(query, {"match_id": match_id})
    overall_stats = cu.fetchone()[0]

    query = '''
    SELECT
      array_agg(m.medal_short)
    FROM (
      SELECT DISTINCT medal_id
      FROM scoreboards_medals
      WHERE match_id = %(match_id)s
    ) sm
    LEFT JOIN medals m ON m.medal_id = sm.medal_id
    '''
    cu.execute(query, {"match_id": match_id})
    medals_available = cu.fetchone()[0]

    query = '''
    SELECT
      array_agg(w.weapon_short)
    FROM (
      SELECT DISTINCT weapon_id
      FROM scoreboards_weapons
      WHERE match_id = %(match_id)s
    ) sw
    LEFT JOIN weapons w ON w.weapon_id = sw.weapon_id
    '''
    cu.execute(query, {"match_id": match_id})
    weapons_available = cu.fetchone()[0]

    result = {
      "summary": summary,
      "player_stats": {"weapons": player_weapon_stats, "medals": player_medal_stats},
      "team_stats": {
        "overall":        overall_stats
      },
      "weapons_available": weapons_available,
      "medals_available": medals_available,
      "ok": True
    }
  except Exception as e:
    db.rollback()
    traceback.print_exc(file=sys.stderr)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }
  finally:
    cu.close()
    db.close()

  return result


def get_last_matches( gametype = None, steam_id = None, page = 0 ):
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

    query = '''
    SELECT
      json_build_object(
        'match_id', m.match_id,
        'datetime', to_char(to_timestamp(timestamp), 'YYYY-MM-DD HH24:MI'),
        'timestamp', timestamp,
        'gametype', g.gametype_short,
        'team1_score', m.team1_score,
        'team2_score', m.team2_score,
        'map', mm.map_name
      ),
      count(*) OVER () AS count
    FROM
      matches m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN maps mm ON mm.map_id = m.map_id
    {WHERE_CLAUSE}
    ORDER BY timestamp DESC
    OFFSET %(offset)s
    LIMIT %(limit)s
    '''.replace("{WHERE_CLAUSE}\n", "" if len(where_clauses) == 0 else "WHERE " + " AND ".join(where_clauses))

    cu.execute( query, params )

    matches = []
    overall_match_count = 1
    for row in cu:
      item = dict(row[0])
      item["timedelta"] = humanize.naturaltime( datetime.now() - datetime.fromtimestamp(item['timestamp'] ) )
      matches.append( item )
      overall_match_count = row[1]

    result = {
      "ok": True,
      "page_count": ceil(overall_match_count / MATCH_LIST_ITEM_COUNT),
      "title": title,
      "matches": matches
    }

  except Exception as e:
    db.rollback()
    traceback.print_exc(file=sys.stderr)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e)
    }

  cu.close()
  db.close()

  return result
