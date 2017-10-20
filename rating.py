#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import re
import sys
import traceback
import psycopg2
import trueskill
import humanize
from functools import reduce
from urllib.parse import urlparse
from datetime import datetime
from config import cfg
from sqlalchemy.exc import ProgrammingError
from math import ceil

GAMETYPE_IDS = {}
MEDAL_IDS    = {}
WEAPON_IDS   = {}
LAST_GAME_TIMESTAMPS = {}
MEDALS_AVAILABLE  = []
WEAPONS_AVAILABLE = []

MIN_ALIVE_TIME_TO_RATE = 60*10
MIN_PLAYER_COUNT_TO_RATE = {
  "ad":  cfg['min_player_count_in_match_to_rate_ad'],
  "ctf": cfg['min_player_count_in_match_to_rate_ctf'],
  "tdm": cfg['min_player_count_in_match_to_rate_tdm']
}
MIN_PLAYER_COUNT_TO_RATE["tdm2v2"] = 4
USE_AVG_PERF = {
  "ad":      cfg['use_avg_perf_ad'],
  "ctf":     cfg['use_avg_perf_ctf'],
  "tdm":     cfg['use_avg_perf_tdm'],
  "tdm2v2":  cfg['use_avg_perf_tdm2v2']
}
MAX_RATING = 1000
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
    gr.last_played_timestamp > %s AND
    gr.gametype_id = %s
  ORDER BY gr.mean DESC
'''

def db_connect():
  result = urlparse( cfg["db_url"] )
  username = result.username
  password = result.password
  database = result.path[1:]
  hostname = result.hostname
  port = result.port
  return psycopg2.connect(database = database, user = username, password = password, host = hostname, port = port)

# https://github.com/PredatH0r/XonStat/blob/380fbd4aeafb722c844f66920fb850a0ad6821d3/xonstat/views/submission.py#L19
def parse_stats_submission(body):
  """
  Parses the POST request body for a stats submission
  """
  # storage vars for the request body
  game_meta = {}
  events = {}
  players = []
  teams = []

  # we're not in either stanza to start
  in_P = in_Q = False

  for line in body.split('\n'):
    try:
      (key, value) = line.strip().split(' ', 1)

      if key not in 'P' 'Q' 'n' 'e' 't' 'i':
        game_meta[key] = value

      if key == 'Q' or key == 'P':
        #log.debug('Found a {0}'.format(key))
        #log.debug('in_Q: {0}'.format(in_Q))
        #log.debug('in_P: {0}'.format(in_P))
        #log.debug('events: {0}'.format(events))

        # check where we were before and append events accordingly
        if in_Q and len(events) > 0:
          #log.debug('creating a team (Q) entry')
          teams.append(events)
          events = {}
        elif in_P and len(events) > 0:
          #log.debug('creating a player (P) entry')
          players.append(events)
          events = {}

        if key == 'P':
          #log.debug('key == P')
          in_P = True
          in_Q = False
        elif key == 'Q':
          #log.debug('key == Q')
          in_P = False
          in_Q = True

        events[key] = value

      if key == 'e':
        (subkey, subvalue) = value.split(' ', 1)
        events[subkey] = subvalue
      if key == 'n':
        events[key] = value
      if key == 't':
        events[key] = value
    except:
      # no key/value pair - move on to the next line
      pass

  # add the last entity we were working on
  if in_P and len(events) > 0:
    players.append(events)
  elif in_Q and len(events) > 0:
    teams.append(events)

  return {"game_meta": game_meta, "players": players, "teams": teams}


def is_instagib(data):
  '''
  Checks if match is played with instagib mode
  '''
  def is_player_using_weapon( player, weapon ):
    try:
      return True if player['acc-' + weapon + '-cnt-fired'] == '0' else False
    except KeyError:
      return True 

  def is_player_using_railgun_and_gauntlet_only( player ):
    return all( map( lambda weapon: is_player_using_weapon( player, weapon), ['mg', 'sg', 'gl', 'rl', 'lg', 'pg', 'hmg', 'bfg', 'cg', 'ng', 'pm', 'gh'] ) )

  return all( map ( lambda player: is_player_using_railgun_and_gauntlet_only( player ), data['players'] ) )


def is_tdm2v2(data):
  return data["game_meta"]["G"] == "tdm" and len(data["players"]) == 4


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
    LIMIT %s
    OFFSET %s'''
    cu.execute(query, [LAST_GAME_TIMESTAMPS[ gametype_id ]-KEEPING_TIME if show_inactive is False else 0, gametype_id, cfg["player_count_per_page"], cfg["player_count_per_page"]*page])

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


def clean_name(name):
  for s in ['0', '1', '2', '3', '4', '5', '6', '7']:
    name = name.replace("^" + s, "")

  if name == "":
    name = "unnamed"

  return name


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


def get_player_info(steam_id):

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
          s.old_mean IS NOT NULL AND
          s.steam_id = %s AND
          m.gametype_id = %s
        ORDER BY m.timestamp DESC
        LIMIT 50
      ) m ON m.gametype_id = g.gametype_id
      LEFT JOIN (''' + SQL_TOP_PLAYERS_BY_GAMETYPE + ''') rt ON rt.steam_id = p.steam_id
      WHERE
        p.steam_id = %s AND
        g.gametype_id = %s
      ORDER BY m.timestamp ASC
      '''
      cu.execute(query, [steam_id, gametype_id, LAST_GAME_TIMESTAMPS[ gametype_id ]-KEEPING_TIME, gametype_id, steam_id, gametype_id])
      for row in cu.fetchall():
        result[ "_id" ] = str(row[0])
        result[ "name" ] = row[1]
        result[ "model" ] = row[2]
        if gametype not in result and row[4] != None:
          result[ gametype ] = {"rating": round(row[4], 2), "n": row[5], "history": [], "rank": row[9], "max_rank": row[10]}
        if row[8] != None:
          result[ gametype ][ "history" ].append({"match_id": row[6], "timestamp": row[7], "rating": round(row[8], 2)})

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


def get_player_info2( steam_id ):

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


def get_factory_id( cu, factory ):
  cu.execute( "SELECT factory_id FROM factories WHERE factory_short = %s", [factory] )
  try:
    return cu.fetchone()[0]
  except TypeError:
    cu.execute("INSERT INTO factories (factory_id, factory_short) VALUES (nextval('factory_seq'), %s) RETURNING factory_id", [factory])
    return cu.fetchone()[0]


def get_map_id( cu, map_name, dont_create = False ):
  map_name = map_name.lower()
  cu.execute( "SELECT map_id FROM maps WHERE map_name = %s", [map_name] )
  try:
    return cu.fetchone()[0]
  except TypeError:
    if dont_create:
      return None
    cu.execute("INSERT INTO maps (map_id, map_name) VALUES (nextval('map_seq'), %s) RETURNING map_id", [map_name])
    return cu.fetchone()[0]


def get_for_balance_plugin( steam_ids ):
  """
  Outputs player ratings compatible with balance.py plugin from miqlx-plugins

  Args:
    steam_ids (list): array of steam ids

  Returns:
    on success:
    {
      "ok": True
      "players": [...],
      "deactivated": []
    }

    on fail:
    {
      "ok": False
      "message": "error message"
    }
  """
  players = {}
  result = []
  try:

    db = db_connect()
    cu = db.cursor()

    query = '''
    SELECT
      steam_id, gametype_short, mean, n
    FROM
      gametype_ratings gr
    LEFT JOIN
      gametypes gt ON gr.gametype_id = gt.gametype_id
    WHERE
      steam_id IN %s'''
    cu.execute( query, [tuple(steam_ids)] )
    for row in cu.fetchall():
      steam_id = str(row[0])
      gametype = row[1]
      rating   = round(row[2], 2)
      n        = row[3]
      if steam_id not in players:
        players[ steam_id ] = {"steamid": steam_id}
      players[ steam_id ][ gametype ] = {"games": n, "elo": rating}

    for steam_id, data in players.items():
      result.append( data )
    result = {
      "ok": True,
      "players": result,
      "deactivated": []
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


def get_for_balance_plugin_for_certain_map( steam_ids, gametype, mapname ):
  """
  Outputs player ratings compatible with balance.py plugin from miqlx-plugins

  Args:
    steam_ids (list): array of steam ids
    gametype (str): short gametype
    mapname (str): short mapname

  Returns:
    on success:
    {
      "ok": True
      "players": [...],
      "deactivated": []
    }

    on fail:
    {
      "ok": False
      "message": "error message"
    }
  """
  players = {}
  result = []
  try:

    db = db_connect()
    cu = db.cursor()
    
    try:
      gametype_id = GAMETYPE_IDS[ gametype ]
    except KeyError:
      raise Exception("Invalid gametype: " + gametype)

    query_template = '''
      SELECT
        AVG(t.match_rating), MAX(t.n)
      FROM (
        SELECT
          s.match_perf as match_rating, count(*) OVER() AS n
        FROM
          scoreboards s
        LEFT JOIN matches m ON m.match_id = s.match_id
        WHERE s.steam_id = %s AND m.gametype_id = %s {CLAUSE}
        ORDER BY m.timestamp DESC
        LIMIT %s
      ) t;'''

    query_common = query_template.replace("{CLAUSE}", "")
    query_by_map = query_template.replace("{CLAUSE}", "AND m.map_id = %s")

    # getting common perfomance
    for steam_id in steam_ids:
      cu.execute( query_common, [steam_id, gametype_id, MOVING_AVG_COUNT] )
      row = cu.fetchone()
      if row[0] == None:
        continue
      steam_id = str(steam_id)
      rating   = round(row[0], 2)
      if steam_id not in players:
        players[ steam_id ] = {"steamid": steam_id}
      players[ steam_id ][ gametype ] = {"games": 0, "elo": rating}

    # checking, if map is played ever?
    map_id = get_map_id(cu, mapname, dont_create = True)
    if map_id == None:
      raise KeyError("Unknown map: " + mapname)

    # getting map perfomance
    for steam_id in steam_ids:
      cu.execute( query_by_map, [steam_id, gametype_id, map_id, MOVING_AVG_COUNT] )
      row = cu.fetchone()
      if row[0] == None:
        continue
      steam_id = str(steam_id)
      rating   = round(row[0], 2)
      n        = row[1]
      players[ steam_id ][ gametype ] = {"games": n, "elo": rating}

    for steam_id, data in players.items():
      result.append( data )
    result = {
      "ok": True,
      "players": result,
      "deactivated": []
    }

  except KeyError as e:
    db.rollback()
    traceback.print_exc(file=sys.stderr)
    result = {
      "ok": True,
      "players": list(players.values()),
      "deactivated": []
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


def count_player_match_perf( gametype, player_data ):
  alive_time    = int( player_data["alivetime"] )
  score         = int( player_data["scoreboard-score"] )
  damage_dealt  = int( player_data["scoreboard-pushes"] )
  damage_taken  = int( player_data["scoreboard-destroyed"] )
  frags_count   = int( player_data["scoreboard-kills"] )
  deaths_count  = int( player_data["scoreboard-deaths"] )
  capture_count = int( player_data["medal-captures"] )
  defends_count = int( player_data["medal-defends"] )
  assists_count = int( player_data["medal-assists"] )
  win           = 1 if "win" in player_data else 0

  if alive_time < MIN_ALIVE_TIME_TO_RATE:
    return None
  else:
    time_factor   = 1200./alive_time

  return {
    "ad": ( damage_dealt/100 + frags_count + capture_count ) * time_factor,
    "ctf": ( damage_dealt/damage_taken * ( score + damage_dealt/20 ) * time_factor ) / 2.35 + win*300,
    "tdm2v2": ( 0.5 * (frags_count - deaths_count) + 0.004 * (damage_dealt - damage_taken) + 0.003 * damage_dealt ) * time_factor,
    "tdm": ( 0.5 * (frags_count - deaths_count) + 0.004 * (damage_dealt - damage_taken) + 0.003 * damage_dealt ) * time_factor
  }[gametype]


def count_multiple_players_match_perf( gametype, all_players_data ):

  result = {}
  temp = []
  sum_perf = 0
  for player in all_players_data:
    team     = int(player["t"]) if "t" in player else 0
    steam_id = int(player["P"])
    perf     = count_player_match_perf( gametype, player ) if MIN_PLAYER_COUNT_TO_RATE[ gametype ] <= len(all_players_data) else None
    if perf != None:
      temp.append({
        "team":     team,
        "steam_id": steam_id,
        "perf":     perf
      })
      sum_perf += perf
    if team not in result:
      result[ team ] = {}
    result[ team ][ steam_id ] = { "perf": perf }

  return result


def post_process_avg_perf(cu, match_id, gametype_id, match_timestamp):
  """
  Updates players' ratings after playing match_id (using avg. perfomance)

  """
  def extra_factor( gametype, matches, wins, losses ):
    try:
      return {
        "tdm": (1 + (0.15 * (wins / matches - losses / matches)))
      }[gametype]
    except KeyError:
      return 1

  global LAST_GAME_TIMESTAMPS
  cu.execute("SELECT s.steam_id, team, match_perf, gr.mean FROM scoreboards s LEFT JOIN gametype_ratings gr ON gr.steam_id = s.steam_id AND gr.gametype_id = %s WHERE match_perf IS NOT NULL AND match_id = %s", [gametype_id, match_id])

  rows = cu.fetchall()
  for row in rows:
    steam_id   = row[0]
    team       = row[1]
    match_perf = row[2]
    old_rating = row[3]

    cu.execute("UPDATE scoreboards SET old_mean = %s, old_deviation = 0 WHERE match_id = %s AND steam_id = %s AND team = %s", [old_rating, match_id, steam_id, team])
    assert cu.rowcount == 1

    if old_rating == None:
      new_rating = match_perf
    else:
      query_string = '''
      SELECT
        COUNT(1),
        SUM(win) as wins,
        SUM(loss) as losses,
        AVG(rating)
      FROM (
        SELECT
          CASE
            WHEN m.team1_score > m.team2_score AND s.team = 1 THEN 1
            WHEN m.team2_score > m.team1_score AND s.team = 2 THEN 1
            ELSE 0
          END as win,
          CASE
            WHEN m.team1_score > m.team2_score AND s.team = 1 THEN 0
            WHEN m.team2_score > m.team1_score AND s.team = 2 THEN 0
            ELSE 1
          END as loss,
          s.match_perf as rating
        FROM
          matches m
        LEFT JOIN
          scoreboards s on s.match_id = m.match_id
        WHERE
          s.steam_id = %s AND
          m.gametype_id = %s AND
          (m.post_processed = TRUE OR m.match_id = %s) AND
          s.match_perf IS NOT NULL
        ORDER BY m.timestamp DESC
        LIMIT %s
      ) t'''
      cu.execute(query_string, [steam_id, gametype_id, match_id, MOVING_AVG_COUNT])
      row = cu.fetchone()
      gametype = [k for k, v in GAMETYPE_IDS.items() if v == gametype_id][0]
      new_rating = row[3] * extra_factor( gametype, row[0], row[1], row[2] )

    cu.execute("UPDATE scoreboards SET new_mean = %s, new_deviation = 0 WHERE match_id = %s AND steam_id = %s AND team = %s", [new_rating, match_id, steam_id, team])
    assert cu.rowcount == 1

    cu.execute("UPDATE gametype_ratings SET mean = %s, deviation = 0, n = n + 1, last_played_timestamp = %s WHERE steam_id = %s AND gametype_id = %s", [new_rating, match_timestamp, steam_id, gametype_id])
    if cu.rowcount == 0:
      cu.execute("INSERT INTO gametype_ratings (steam_id, gametype_id, mean, deviation, last_played_timestamp, n) VALUES (%s, %s, %s, 0, %s, 1)", [steam_id, gametype_id, new_rating, match_timestamp])
    assert cu.rowcount == 1

  cu.execute("UPDATE matches SET post_processed = TRUE WHERE match_id = %s", [match_id])
  assert cu.rowcount == 1

  LAST_GAME_TIMESTAMPS[ gametype_id ] = match_timestamp


def post_process_trueskill(cu, match_id, gametype_id, match_timestamp):
  """
  Updates players' ratings after playing match_id (using trueskill)

  """
  global LAST_GAME_TIMESTAMPS
  cu.execute("SELECT team2_score > team1_score, team2_score < team1_score FROM matches WHERE match_id = %s", [ match_id ])
  row = cu.fetchone()
  team_ranks = [ row[0], row[1] ]

  cu.execute('''
    SELECT
      s.steam_id,
      team,
      s.match_perf,
      gr.mean,
      gr.deviation
    FROM
      scoreboards s
    LEFT JOIN (
      SELECT steam_id, mean, deviation
      FROM gametype_ratings
      WHERE gametype_id = %s
    ) gr ON gr.steam_id = s.steam_id
    WHERE
      match_perf IS NOT NULL AND
      match_id = %s
    ''', [gametype_id, match_id])

  team_ratings_old = [ [], [] ]
  team_ratings_new = [ [], [] ]
  team_steam_ids   = [ [], [] ]
  rows = cu.fetchall()
  for row in rows:
    steam_id     = row[0]
    team         = row[1]
    # match_perf   = row[2]
    mean         = row[3]
    deviation    = row[4]

    try:
      team_ratings_old[ team - 1 ].append( trueskill.Rating( mean, deviation ) )
      team_steam_ids  [ team - 1 ].append( steam_id )
    except KeyError:
      continue

  if len( team_ratings_old[0] ) == 0 or len( team_ratings_old[1] ) == 0:
    cu.execute("UPDATE matches SET post_processed = TRUE WHERE match_id = %s", [match_id])
    assert cu.rowcount == 1

    LAST_GAME_TIMESTAMPS[ gametype_id ] = match_timestamp
    return

  team1_ratings, team2_ratings = trueskill.rate( team_ratings_old, ranks=team_ranks )
  team_ratings_new = [team1_ratings, team2_ratings]

  steam_ids   = team_steam_ids[0] + team_steam_ids[1]
  new_ratings = team1_ratings + team2_ratings
  old_ratings = team_ratings_old[0] + team_ratings_old[1]

  assert len(steam_ids) == len(new_ratings) == len(old_ratings)

  steam_ratings = {}
  for i in range( len(steam_ids) ):
    steam_id = steam_ids[i]

    if steam_id in steam_ratings: # player played for both teams. Ignoring...
      del steam_ratings[ steam_id ]

    steam_ratings[ steam_id ] = {
      "old": old_ratings[i],
      "new": new_ratings[i],
      "team": 1 if i < len(team1_ratings) else 2
    }

  for steam_id, ratings in steam_ratings.items():
    cu.execute('''
      UPDATE scoreboards
      SET
        old_mean = %s, old_deviation = %s,
        new_mean = %s, new_deviation = %s
      WHERE match_id = %s AND steam_id = %s AND team = %s
    ''', [ratings["old"].mu, ratings["old"].sigma, ratings["new"].mu, ratings["new"].sigma, match_id, steam_id, ratings["team"]])
    assert cu.rowcount == 1

    cu.execute("UPDATE gametype_ratings SET mean = %s, deviation = %s, n = n + 1, last_played_timestamp = %s WHERE steam_id = %s AND gametype_id = %s", [ratings['new'].mu, ratings['new'].sigma, match_timestamp, steam_id, gametype_id])
    if cu.rowcount == 0:
      cu.execute("INSERT INTO gametype_ratings (steam_id, gametype_id, mean, deviation, last_played_timestamp, n) VALUES (%s, %s, %s, %s, %s, 1)", [steam_id, gametype_id, ratings['new'].mu, ratings['new'].sigma, match_timestamp])
    assert cu.rowcount == 1

  cu.execute("UPDATE matches SET post_processed = TRUE WHERE match_id = %s", [match_id])
  assert cu.rowcount == 1

  LAST_GAME_TIMESTAMPS[ gametype_id ] = match_timestamp


def post_process(cu, match_id, gametype_id, match_timestamp):
  if USE_AVG_PERF[ gametype_id ]:
    return post_process_avg_perf(cu, match_id, gametype_id, match_timestamp)
  else:
    return post_process_trueskill(cu, match_id, gametype_id, match_timestamp)


def submit_match(data):
  """
  Match report handler

  Args:
    data (str): match report

  Returns: {
      "ok: True/False - on success/fail
      "message":      - operation result description
      "match_id":     - match_id of match_report
    }
  """
  try:
    match_id = None

    if type(data).__name__ == 'str':
      data = parse_stats_submission( data )

    if is_instagib(data):
      data["game_meta"]["G"] = "i" + data["game_meta"]["G"]

    if is_tdm2v2(data):
      data["game_meta"]["G"] = "tdm2v2"

    match_id = data["game_meta"]["I"]

    if data["game_meta"]["G"] not in GAMETYPE_IDS:
      return {
        "ok": False,
        "message": "gametype is not accepted: " + data["game_meta"]["G"],
        "match_id": match_id
      }

    db = db_connect()
    cu = db.cursor()

    team_scores = [None, None]
    team_index = -1
    for team_data in data["teams"]:
      team_index = int( team_data["Q"].replace("team#", "") ) - 1
      for key in ["scoreboard-rounds", "scoreboard-caps", "scoreboard-score"]:
        if key in team_data:
          team_scores[team_index] = int(team_data[key])
    team1_score, team2_score = team_scores

    match_timestamp = int( data["game_meta"]["1"] )
    cu.execute("INSERT INTO matches (match_id, gametype_id, factory_id, map_id, timestamp, duration, team1_score, team2_score, post_processed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", [
      match_id,
      GAMETYPE_IDS[ data["game_meta"]["G"] ],
      get_factory_id( cu, data["game_meta"]["O"] ),
      get_map_id( cu, data["game_meta"]["M"] ),
      match_timestamp,
      int( data["game_meta"]["D"] ),
      team1_score,
      team2_score,
      cfg["run_post_process"]
    ])

    player_match_ratings = count_multiple_players_match_perf( data["game_meta"]["G"], data["players"] )
    for player in data["players"]:
      player["P"] = int(player["P"])
      team = int(player["t"]) if "t" in player else 0

      cu.execute( '''INSERT INTO players (
        steam_id,
        name,
        model,
        last_played_timestamp
      ) VALUES (%s, %s, %s, %s)
      ON CONFLICT (steam_id) DO UPDATE SET (name, model, last_played_timestamp) = (%s, %s, %s)
      WHERE players.last_played_timestamp < %s''', [
        player["P"],
        player["n"],
        player["playermodel"],
        match_timestamp,
        player["n"],
        player["playermodel"],
        match_timestamp,
        match_timestamp
      ])

      cu.execute('''INSERT INTO scoreboards (
        match_id,
        steam_id,
        frags,
        deaths,
        damage_dealt,
        damage_taken,
        score,
        match_perf,
        alive_time,
        team
      ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', [
        match_id,
        player["P"],
        int( player["scoreboard-kills"] ),
        int( player["scoreboard-deaths"] ),
        int( player["scoreboard-pushes"] ),
        int( player["scoreboard-destroyed"] ),
        int( player["scoreboard-score"] ),
        player_match_ratings[ team ][ player["P"] ][ "perf" ],
        int( player["alivetime"] ),
        team
      ])

      for weapon, weapon_id in WEAPON_IDS.items():
        cu.execute("INSERT INTO scoreboards_weapons (match_id, steam_id, team, weapon_id, frags, hits, shots) VALUES (%s, %s, %s, %s, %s, %s, %s)", [
          match_id,
          player["P"],
          team,
          weapon_id,
          int( player["acc-" + weapon + "-frags"] ),
          int( player["acc-" + weapon + "-cnt-hit"] ),
          int( player["acc-" + weapon + "-cnt-fired"] )
        ])

      for medal, medal_id in MEDAL_IDS.items():
        cu.execute("INSERT INTO scoreboards_medals (match_id, steam_id, team, medal_id, count) VALUES (%s, %s, %s, %s, %s)", [
          match_id,
          player["P"],
          team,
          medal_id,
          int( player["medal-" + medal] )
        ])

    # post processing
    if cfg["run_post_process"] == True:
      post_process( cu, match_id, GAMETYPE_IDS[ data["game_meta"]["G"] ], match_timestamp )
      result = {
        "ok": True,
        "message": "done",
        "match_id": match_id
      }
    else:
      result = {
        "ok": True,
        "message": "skipped post processing",
        "match_id": match_id
      }

    db.commit()
  except Exception as e:
    db.rollback()
    traceback.print_exc(file=sys.stderr)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e),
      "match_id": match_id
    }

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
        'timestamp',   m.timestamp,
        'datetime',    TO_CHAR(to_timestamp(m.timestamp), 'YYYY-MM-DD HH24:MI'),
        'duration',    TO_CHAR((m.duration || ' second')::interval, 'MI:SS')
      )
    FROM
      matches m
    LEFT JOIN gametypes g ON g.gametype_id = m.gametype_id
    LEFT JOIN factories f ON f.factory_id = m.factory_id
    LEFT JOIN maps mm ON m.map_id = mm.map_id
    WHERE
      match_id = %s;
    '''
    cu.execute(query, [match_id])
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
        LEFT JOIN scoreboards_weapons sw ON sw.match_id = s.match_id AND sw.steam_id = s.steam_id AND sw.team = s.team
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
        LEFT JOIN scoreboards_medals sm ON sm.match_id = s.match_id AND sm.steam_id = s.steam_id AND sm.team = s.team
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
      json_object_agg(t.team, t.player_rating_history)
    FROM (
      SELECT
        t.team,
        json_object_agg(t.steam_id, t.rating_history) as player_rating_history
      FROM (
        SELECT
          t.steam_id, t.team, 
          json_build_object('old_rating', t.old_mean, 'new_rating', t.new_mean, 'match_rating', t.match_perf) AS rating_history
        FROM
          scoreboards t
        WHERE
          t.match_id = %s
      ) t
      GROUP BY t.team
    ) t;
    '''
    cu.execute(query, [match_id])
    rating_history = cu.fetchone()[0]

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
          LEFT JOIN scoreboards_weapons sw ON sw.match_id = s.match_id AND sw.steam_id = s.steam_id AND sw.team = s.team
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
          LEFT JOIN scoreboards_medals sm ON sm.match_id = s.match_id AND sm.steam_id = s.steam_id AND sm.team = s.team
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

    result = {
      "summary": summary,
      "player_stats": {"weapons": player_weapon_stats, "medals": player_medal_stats},
      "team_stats": {
        "rating_history": rating_history,
        "overall":        overall_stats
      },
      "weapons_available": WEAPONS_AVAILABLE,
      "medals_available": MEDALS_AVAILABLE,
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


def get_last_matches( gametype = None, page = 0 ):
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

  try:
    db = db_connect()
    cu = db.cursor()

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
    OFFSET %s
    LIMIT %s
    '''.replace("{WHERE_CLAUSE}\n", "" if gametype == None else "WHERE m.gametype_id = %s")

    params = [ ]
    if gametype != None:
      params.append( GAMETYPE_IDS[ gametype ] )
    params.append( page * MATCH_LIST_ITEM_COUNT )
    params.append( MATCH_LIST_ITEM_COUNT )

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


def reset_gametype_ratings( gametype ):
  """
  Resets ratings for gametype
  """
  if gametype not in GAMETYPE_IDS:
    print("gametype is not accepted: " + gametype)
    return False

  gametype_id = GAMETYPE_IDS[gametype]
  result = False
  try:
    db = db_connect()
    cu = db.cursor()
    cw = db.cursor()

    cw.execute('UPDATE matches SET post_processed = FALSE WHERE gametype_id = %s', [gametype_id])
    cw.execute('UPDATE gametype_ratings SET mean = %s, deviation = %s, n = 0 WHERE gametype_id = %s', [trueskill.MU, trueskill.SIGMA, gametype_id])
    scoreboard_query = '''
    SELECT
      s.match_id,
      MIN(m.team1_score) AS team1_score,
      MIN(m.team2_score) AS team1_score,
      array_agg(json_build_object(
        'P',                    s.steam_id,
        't',                    s.team,
        'alivetime',            s.alive_time,
        'scoreboard-score',     s.score,
        'scoreboard-pushes',    s.damage_dealt,
        'scoreboard-destroyed', s.damage_taken,
        'scoreboard-kills',     s.frags,
        'scoreboard-deaths',    s.deaths,
        'medal-captures',       mm.medals->'captures',
        'medal-defends',        mm.medals->'defends',
        'medal-assists',        mm.medals->'assists'
      ))
    FROM
      scoreboards s
    LEFT JOIN matches m ON m.match_id = s.match_id
    LEFT JOIN (
      SELECT
        sm.steam_id, sm.team, sm.match_id,
        json_object_agg(mm.medal_short, sm.count) as medals
      FROM
        scoreboards_medals sm
      LEFT JOIN
        medals mm ON mm.medal_id = sm.medal_id
      GROUP BY sm.steam_id, sm.team, sm.match_id
    ) mm ON mm.match_id = s.match_id AND s.steam_id = mm.steam_id AND s.team = mm.team
    WHERE gametype_id = %s
    GROUP BY s.match_id;
    '''

    cu.execute(scoreboard_query, [gametype_id])
    for row in cu:
      match_id = row[0]
      team1_score = row[1]
      team2_score = row[2]
      all_players_data = []
      for player in row[3]:
        if player['t'] == 1 and team1_score > team2_score:
          player['win'] = 1
        if player['t'] == 2 and team1_score < team2_score:
          player['win'] = 1
        all_players_data.append(player.copy())
      print(match_id)
      player_match_ratings = count_multiple_players_match_perf( gametype, all_players_data )

      for player in all_players_data:
        player["P"] = int(player["P"])
        team = int(player["t"]) if "t" in player else 0

        cw.execute(
          'UPDATE scoreboards SET match_perf = %s, new_mean = NULL, old_mean = NULL, new_deviation = NULL, old_deviation = NULL WHERE match_id = %s AND team = %s AND steam_id = %s', [
            player_match_ratings[ team ][ player["P"] ][ "perf" ],
            match_id, team, player["P"]
          ]
        )

    db.commit()
    result = True

  except Exception as e:
    db.rollback()
    traceback.print_exc(file=sys.stderr)
  finally:
    cu.close()
    db.close()

  return result


db = db_connect()
cu = db.cursor()
cu.execute("SELECT gametype_id, gametype_short FROM gametypes")
for row in cu.fetchall():
  GAMETYPE_IDS[ row[1] ] = row[0]
  USE_AVG_PERF[ row[0] ] = USE_AVG_PERF[ row[1] ]

cu.execute("SELECT medal_id, medal_short FROM medals ORDER BY medal_id")
for row in cu.fetchall():
  MEDAL_IDS[ row[1] ] = row[0]
  MEDALS_AVAILABLE.append( row[1] )

cu.execute("SELECT weapon_id, weapon_short FROM weapons ORDER BY weapon_id")
for row in cu.fetchall():
  WEAPON_IDS[ row[1] ] = row[0]
  WEAPONS_AVAILABLE.append( row[1] )

if cfg["run_post_process"]:
  cu.execute("SELECT match_id, gametype_id, timestamp FROM matches WHERE post_processed = FALSE ORDER BY timestamp ASC")
  for row in cu.fetchall():
    print("running post process: " + str(row[0]) + "\t" + str(row[2]))
    post_process(cu, row[0], row[1], row[2])
    db.commit()

for _, gametype_id in GAMETYPE_IDS.items():
  LAST_GAME_TIMESTAMPS[ gametype_id ] = 0
  cu.execute("SELECT timestamp FROM matches WHERE gametype_id = %s ORDER BY timestamp DESC LIMIT 1", [gametype_id])
  for row in cu.fetchall():
    LAST_GAME_TIMESTAMPS[ gametype_id ] = row[0]

cu.close()
db.close()
