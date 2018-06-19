# -*- coding: utf-8 -*-
#

import requests
from common import log_exception
from conf import settings as cfg
from db import db_connect, cache
from submission import get_map_id

GAMETYPE_IDS = cache.GAMETYPE_IDS
MOVING_AVG_COUNT = cfg['moving_average_count']

def prepare_result( players ):
  playerinfo = {}

  for steam_id, data in players.items():
    playerinfo[ steam_id ] = {
      'deactivated': False,
      'ratings': data.copy(),
      'allowRating': True,
      'privacy': "public"
    }

  return {
    "ok": True,
    "playerinfo": playerinfo,
    "players": list(players.values()),
    "untracked": [],
    "deactivated": []
  }


def simple( steam_ids ):
  """
  Outputs player ratings compatible with balance.py plugin from minqlx-plugins

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

    result = prepare_result(players)

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


def with_player_info_from_qlstats( steam_ids ):
  result = simple(steam_ids)
  if result['ok'] == False:
    return result

  r = requests.get("https://qlstats.net/elo/" + "+".join(map(lambda id_: str(id_), steam_ids)), timeout = 3)
  if not r.ok:
    return result

  try:
    qlstats_data = r.json()
  except Exception as e:
    log_exception(e)
    return result

  qlstats_data['players'] = result['players']
  for steam_id, info in result['playerinfo'].items():
    print(qlstats_data['playerinfo'][steam_id])
    qlstats_data['playerinfo'][steam_id]['ratings'] = info['ratings']

  return qlstats_data


def for_certain_map( steam_ids, gametype, mapname ):
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

    result = prepare_result(players)

  except KeyError as e:
    db.rollback()
    log_exception(e)
    result = prepare_result(players)

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
