#!/usr/bin/python3
# -*- coding: utf-8 -*-

import requests
from config import cfg
from flask import Flask, jsonify
import rating
import sys
from uuid import UUID
import json
import sys
import os

app = Flask(__name__)
player_ids = {}
PATH = os.path.dirname(os.path.realpath(__file__))

try:
  f = open(PATH + "/player_ids.json", "r")
  player_ids = json.loads( f.read() )
  f.close()
except IOError:
  pass


def get_player_id( steam_id ):
  if steam_id not in player_ids:

    r = requests.get("http://qlstats.net/player/" + steam_id + ".json")
    player_ids[ steam_id ] = r.json()[0]['player']['player_id']
    f = open(PATH + "/player_ids.json", "w")
    f.write( json.dumps(player_ids, indent=2, sort_keys=True) )
    f.close()

  return player_ids[ steam_id ]


@app.route("/scoreboard/<match_id>")
def http_scoreboard_match_id(match_id):
  try:
    if len(match_id) != len('12345678-1234-5678-1234-567812345678'):
      raise ValueError()
    UUID(match_id)
  except ValueError:
    resp = jsonify(ok=False, message="invalid match_id")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

  scoreboard = rating.get_scoreboard(match_id)
  if scoreboard["ok"] == True:

    steam_ids = {}
    for steam_id, _ in scoreboard["player_stats"]["weapons"].items():
      steam_ids[ get_player_id( steam_id ) ] = steam_id
    scoreboard.update({"steam_ids": steam_ids})

  resp = jsonify(**scoreboard)
  resp.headers['Access-Control-Allow-Origin'] = '*'
  return resp


if __name__ == "__main__":
  app.run( host = "0.0.0.0", port = 7083 )
