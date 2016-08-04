#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import sys
import traceback
import psycopg2
from urllib.parse import urlparse
from config import cfg
#from sqlalchemy.exc import IntegrityError

GAMETYPE_IDS = {}
MEDAL_IDS    = {}
WEAPON_IDS   = {}


def db_connect():
  result = urlparse( cfg["db_url"] )
  username = result.username
  password = result.password
  database = result.path[1:]
  hostname = result.hostname
  return psycopg2.connect(database = database, user = username, password = password, host = hostname)


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

      # Server (S) and Nick (n) fields can have international characters.
      if key in 'S' 'n':
        value = unicode(value, 'utf-8')

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


def get_list(gametype, page):
  return {"ok": False, "message": "not implemented"}

def get_player_info(player_id):
  return {"ok": False, "message": "not implemented"}

def get_for_balance_plugin(ids):
  return {"ok": False, "message": "not implemented"}


def submit_match(body):
  """
  Match report handler

  Args:
    body (str): match report

  Returns: {
      "ok: True/False - on success/fail
      "message":      - operation result description
      "match_id":     - match_id of match_report
    }
  """
  try:
    if type(body).__name__ == 'str':
      body = parse_stats_submission( body )

    if is_instagib(data):
      data["game_meta"]["G"] = "i" + data["game_meta"]["G"]

    if data["game_meta"]["G"] not in GAMETYPES_AVAILABLE:
      return {
        "ok": False,
        "message": "gametype is not accepted: " + data["game_meta"]["G"],
        "match_id": data["game_meta"]["I"]
      }

    db = db_connect()

  except Exception as e:
    traceback.print_exc(file=sys.stderr)
    return {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e),
      "match_id": None
    }

  try:
    # ToDo: medals
    # ToDo: weapons
    # 
    pass
  except Exception as e:
    traceback.print_exc(file=sys.stderr)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e),
      "match_id": data["game_meta"]["I"]
    }
  finally:
    db.close()

  return result


db = db_connect()
cu = db.cursor()
cu.execute("SELECT gametype_id, gametype_short FROM gametypes")
for row in cu.fetchall():
  GAMETYPE_IDS[ row[1] ] = row[0]

cu.execute("SELECT medal_id, medal_short FROM medals")
for row in cu.fetchall():
  MEDAL_IDS[ row[1] ] = row[0]

cu.execute("SELECT weapon_id, weapon_short FROM weapons")
for row in cu.fetchall():
  WEAPON_IDS[ row[1] ] = row[0]
