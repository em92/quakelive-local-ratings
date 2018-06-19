# -*- coding: utf-8 -*-
#

import sys
import traceback
from conf import settings as cfg
from db import db_connect, cache
from submission import get_map_id

GAMETYPE_IDS = cache.GAMETYPE_IDS
MOVING_AVG_COUNT = cfg['moving_average_count']

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
