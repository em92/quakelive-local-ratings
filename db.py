# -*- coding: utf-8 -*-
#

from collections import OrderedDict
from urllib.parse import urlparse

import psycopg2

from conf import settings

def db_connect():
  result = urlparse( settings["db_url"] )
  username = result.username
  password = result.password
  database = result.path[1:]
  hostname = result.hostname
  port = result.port
  return psycopg2.connect(database = database, user = username, password = password, host = hostname, port = port)


class Cache:
  def __init__(self):
    self._gametype_ids   = {}
    self._gametype_names = OrderedDict()
    self._medal_ids      = {}
    self._medals         = []
    self._weapon_ids     = {}
    self._weapons        = []

    self.LAST_GAME_TIMESTAMPS = {}

    db = db_connect()
    cu = db.cursor()
    cu.execute("SELECT gametype_id, gametype_short, gametype_name FROM gametypes")
    for row in cu.fetchall():
      self._gametype_ids[ row[1] ] = row[0]
      self._gametype_names[ row[1] ] = row[2]

    cu.execute("SELECT medal_id, medal_short FROM medals ORDER BY medal_id")
    for row in cu.fetchall():
      self._medal_ids[ row[1] ] = row[0]
      self._medals.append( row[1] )

    cu.execute("SELECT weapon_id, weapon_short FROM weapons ORDER BY weapon_id")
    for row in cu.fetchall():
      self._weapon_ids[ row[1] ] = row[0]
      self._weapons.append( row[1] )

    for _, gametype_id in self._gametype_ids.items():
      self.LAST_GAME_TIMESTAMPS[ gametype_id ] = 0
      cu.execute("SELECT timestamp FROM matches WHERE gametype_id = %s ORDER BY timestamp DESC LIMIT 1", [gametype_id])
      for row in cu.fetchall():
        self.LAST_GAME_TIMESTAMPS[ gametype_id ] = row[0]

    cu.close()
    db.close()


  @property
  def GAMETYPE_IDS(self):
    return self._gametype_ids.copy()


  @property
  def GAMETYPE_NAMES(self):
    return self._gametype_names.copy()


  @property
  def MEDAL_IDS(self):
    return self._medal_ids.copy()


  @property
  def MEDALS_AVAILABLE(self):
    return self._medals[:]


  @property
  def WEAPON_IDS(self):
    return self._weapon_ids.copy()


  @property
  def WEAPONS_AVAILABLE(self):
    return self._weapons[:]


cache = Cache()
