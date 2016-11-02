#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from dump_qlstats_data import download_stats
from rating import db_connect
from os.path import isfile


def main(args):
  try:
    path = args[1]
    if path.endswith("/") == False:
      path += "/"
  except KeyError:
    path = "./"

  db = db_connect()

  cu = db.cursor()
  cu.execute("SELECT match_id, timestamp FROM matches")
  for row in cu.fetchall():
    if isfile(path + row[0] + ".json.gz") == False:
      download_stats(row[0], row[1], path)
  db.close()
  return 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv))
