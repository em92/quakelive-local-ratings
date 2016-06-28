#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from datetime import datetime
from dump_qlstats_data import connect_to_database

GAMETYPES_AVAILABLE = ["ad", "ctf", "tdm"]

def main(args):

  try:
    db = connect_to_database()

  except Exception as e:
    print("error: " + str(e))
    return 1

  for gametype in GAMETYPES_AVAILABLE:
    print( gametype )
    options = { gametype + ".history.timestamp": { "$ne": None }, gametype + ".history.match_id": None }
    for player in db.players.find(options):
      print( player["_id"] )
      history_result = []
      for history_item in player[gametype]["history"]:
        match = db.matches.find_one( { "gametype": gametype, "timestamp": history_item["timestamp"] } )
        print( match["_id"] )
        history_item['match_id'] = match["_id"]
        history_result.append( history_item )
        result = { "timestamp": match['timestamp'], "rating": player[gametype]['rating'] }
      db.players.update( { "_id": player['_id'] }, { "$set": { gametype + ".history": history_result } } )

  return 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv))
