#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import json
import pymongo
import os.path
from dump_qlstats_data import download_stats


def connect_to_database():
  from urllib.parse import urlparse
  
  f = open("cfg.json", "r")
  cfg = json.loads(f.read())
  f.close()

  if "db_url" not in cfg:
    raise ValueError("db_url not found in cfg.json")
  temp = urlparse(cfg['db_url'])

  if temp.scheme != 'mongodb':
    raise ValueError("invalid scheme in db_url (" + temp.scheme + ")")

  if temp.port == None:
    temp.port = 27017

  if any((c in '/\. "$*<>:|?') for c in temp.path[1:]):
    raise ValueError("invalid database name in db_url (" + temp.path[1:] + ")")

  print("server: " + temp.hostname + ":" + str(temp.port))
  print("database: " +temp.path[1:])
  return pymongo.MongoClient(temp.hostname, temp.port)[temp.path[1:]]


def main(args):

  db = connect_to_database()
  cursor = db.matches.find().batch_size(100)
  for match in cursor:
    if os.path.isfile(match['_id'] + ".json.gz") == False:
      download_stats(match['_id'], match['timestamp'])
  cursor.close()

  return 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv))
