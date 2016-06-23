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
    print(gametype)
    for player in db.players.find( { gametype + ".history": None } ):
      options = [
        { "$match": { "gametype": gametype } },
        { "$unwind": "$scoreboard" },
        { "$match": { "scoreboard.steam-id": player["_id"] } },
        { "$group": { "_id": "dummy", "timestamp": { "$max": "$timestamp" } } }
      ]
      try:
        match = None
        for temp in db.matches.aggregate(options):
          match = temp
        result = { "timestamp": match['timestamp'], "rating": player[gametype]['rating'] }
        db.players.update( { "_id": player['_id'] }, { "$push": { gametype + ".history": { "$each": [result] } } } )
        print(player['_id'] + "\t" + gametype + ".timestamp = " + datetime.fromtimestamp(match['timestamp']).strftime('%Y-%m-%d %H:%M:%S') + " / " + str(match['timestamp']))
      except TypeError:
        continue
      except KeyError:
        continue

  return 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv))
