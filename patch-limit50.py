#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from dump_qlstats_data import download, connect_to_database, get_game_results

def main(args):

  try:
    db = connect_to_database()

  except Exception as e:
    print("error: " + str(e))
    return 1

  for match in db.matches.find({"timestamp": None}, {"_id": 1}):
    match_results = get_game_results(match['_id'], False)
    db.matches.update( { "_id": match['_id'] }, { "$set": { "timestamp": match_results["timestamp"] } } )

  return 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv))
