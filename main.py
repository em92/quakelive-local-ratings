#!/usr/bin/python3
# -*- coding: utf-8 -*-

from config import cfg
from flask import Flask, request, jsonify
import rating
import sys

RUN_POST_PROCESS = cfg['run_post_process']
app = Flask(__name__)


@app.route("/elo/<ids>")
@app.route("/elo_b/<ids>")
def http_elo(ids):
  ids = list( map(lambda id_: int(id_), ids.split("+")) )
  return jsonify( **rating.get_for_balance_plugin(ids) )


@app.route("/player/<id>")
def http_player_id(player_id):
  return jsonify( **rating.getPlayerInfo(player_id) )


@app.route("/rating/<gametype>/<int:page>")
def http_rating_gametype_page(gametype, page):
  return jsonify( **rating.getList( gametype, page ) )


@app.route("/rating/<gametype>")
def http_rating_gametype(gametype):
  return http_rating_gametype_page( gametype, 0 )


@app.route("/stats/submit", methods=["POST"])
def http_stats_submit():
  # https://github.com/PredatH0r/XonStat/blob/cfeae1b0c35c48a9f14afa98717c39aa100cde59/feeder/feeder.node.js#L989
  if request.headers.get("X-D0-Blind-Id-Detached-Signature") != "dummy":
    print(request.remote_addr + ": signature header invalid or not found", file=sys.stderr)
    return jsonify(ok=False, message="signature header invalid or not found"), 403

  if request.remote_addr not in ['::ffff:127.0.0.1', '::1', '127.0.0.1']:
    print(request.remote_addr + ": non-loopback requests are not allowed", file=sys.stderr)
    return jsonify(ok=False, message="non-loopback requests are not allowed"), 403

  result = rating.submit_match(request.data.decode('utf-8'))
  if result["ok"] == False:
    print(result["match_id"] + ": " + result["message"], file=sys.stderr)
    if "match_already_exists" in result:
      return jsonify(**result), 409
    else:
      return jsonify(**result), 422
  else:
    print(result["match_id"] + ": " + result["message"])
    if cfg['run_post_process'] == False:
      result["ok"] = False
      return jsonify(**result), 202
    else:
      return jsonify(**result), 200


if __name__ == "__main__":
    app.run( host = "0.0.0.0", port = cfg['httpd_port'], threaded = True)
