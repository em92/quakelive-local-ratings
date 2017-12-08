# -*- coding: utf-8 -*-
#

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
