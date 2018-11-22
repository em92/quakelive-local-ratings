#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-c", metavar="config.json", help="use the provided config file", default = "cfg.json")
args = parser.parse_args()

from conf import settings as cfg
if not cfg.read_from_file( args.c ):
  sys.exit(1)

from datetime import datetime
# from flask import Flask, request, jsonify, redirect, url_for, make_response, render_template as base_render_template, escape
from urllib.parse import unquote
from werkzeug.contrib.fixers import ProxyFix
from werkzeug.exceptions import NotFound
import rating
import sys
from uuid import UUID

from db import cache
from submission import submit_match

RUN_POST_PROCESS = cfg['run_post_process']
#app = Flask(__name__, static_url_path='/static')
#app.wsgi_app = ProxyFix(app.wsgi_app)

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

app = Starlette()
app.debug = True
app.mount('/static', StaticFiles(directory="static"), name='static')

import blueprints as bp
app.mount('', bp.balance_api)




'''
class try304(object):
  def __init__(self, f):
    self.f = f
    self.__name__ = self.f.__name__

  def __call__(self, *args, **kwargs):
    if 'gametype' in kwargs and type(kwargs['gametype']) is str:
      last_modified = cache.LAST_GAME_TIMESTAMPS[kwargs['gametype']]
    else:
      last_modified = max(cache.LAST_GAME_TIMESTAMPS.values())
    last_modified = datetime.fromtimestamp(last_modified)

    if request.if_modified_since is not None and request.if_modified_since >= last_modified:
      return ('', 304)

    response = make_response(self.f(*args, **kwargs))
    response.last_modified = last_modified
    return response



@app.before_request
def before_request():
  if request.view_args and 'gametype' in request.view_args:
    request.view_args['gametype'] = request.view_args['gametype'].lower()
    if request.view_args['gametype'] not in cache.GAMETYPE_IDS:
      raise NotFound("invalid gametype")


def render_template(template, **context):
  context['gametype_names'] = cache.GAMETYPE_NAMES
  return base_render_template(template, **context)


@app.template_filter('ql_nickname')
def render_ql_nickname( nickname ):
  nickname = str(escape(nickname))
  for i in range(8):
    nickname = nickname.replace("^" + str(i), '</span><span class="qc' + str(i) + '">')
  return '<span class="qc7">' + nickname + '</span>';


@app.template_filter('seconds_to_mmss')
def seconds_to_mmss( value ):
  seconds = int(escape(value))
  m, s = divmod(seconds, 60)
  return "%02d:%02d" % (m, s)


@app.route('/')
@app.route('/matches/')
@app.route('/matches/<int:page>/')
@app.route('/matches/<gametype>/')
@app.route('/matches/<gametype>/<int:page>/')
@app.route("/player/<int:steam_id>/matches/")
@app.route("/player/<int:steam_id>/matches/<int:page>/")
@app.route("/player/<int:steam_id>/matches/<gametype>/")
@app.route("/player/<int:steam_id>/matches/<gametype>/<int:page>/")
@try304
def http_root(gametype = None, steam_id = None, page = 0):
  page_prefix = "/matches"

  if type(gametype) is str:
    page_prefix = page_prefix + "/" + gametype

  if type(steam_id) is int:
    steam_id = str(steam_id)
    page_prefix = "/player/" + steam_id + page_prefix

  return render_template("match_list.html", **rating.get_last_matches( gametype, steam_id, page ),
    gametype = gametype,
    current_page = page,
    page_prefix = page_prefix
  )


@app.route("/ratings/<gametype>/")
@app.route("/ratings/<gametype>/<int:page>/")
@try304
def http_rating_gametype_page(gametype, page = 0):
  show_inactive = request.args.get("show_inactive", False, type=bool)
  return render_template("ratings_list.html", **rating.get_list( gametype, page, show_inactive ),
    gametype = gametype,
    current_page = page,
    show_inactive = show_inactive,
    page_suffix = ("?show_inactive=yes" if show_inactive else ""),
    page_prefix = "/ratings/" + gametype
  )


@app.route("/ratings/<gametype>/<int:page>.json")
@try304
def http_ratings_gametype_page_json(gametype, page):
  return jsonify( **rating.get_list( gametype, page ) )


@app.route("/player/<int:steam_id>")
@try304
def http_player(steam_id):
  return render_template("player_stats.html", **rating.get_player_info(steam_id), steam_id = str(steam_id) )


@app.route("/player/<int:steam_id>.json")
@try304
def http_player_json(steam_id):
  return jsonify( **rating.get_player_info(int(steam_id)) )


@app.route("/deprecated/player/<int:steam_id>.json")
def http_deprected_player_json(steam_id):
  return jsonify( **rating.get_player_info_old(int(steam_id)) )


@app.route("/deprecated/last_24h_matches.json")
def http_deprected_24h_matches():
  from time import time
  return jsonify( **rating.get_last_matches( from_ts = time() - 60*60*24 ) )


@app.route("/steam_api/GetPlayerSummaries/")
def http_steam_api_GetPlayerSummaries():
  ids = request.args.get("steamids")
  if ids == None:
    return jsonify( ok = False, message = "Required parameter 'steamids' is missing" ), 400

  try:
    ids = ids.replace(",", " ").replace("+", " ")
    ids = list( map(lambda id_: int(id_), ids.split(" ")) )
  except ValueError as e:
    return jsonify( ok = False, message = str(e) ), 400

  players = []
  for steam_id in ids:
    player_info = rating.get_player_info( steam_id )
    if player_info["ok"]:
      if "name" in player_info["response"]:
        players.append({
          "personaname": player_info["response"]["name"],
          "steamid": str(steam_id)
        })
    else:
      return jsonify( ok = False, message = player_info["message"] ), 500

  return jsonify( ok = True, response = { "players": players } )


@app.route("/export_rating/<frmt>/<gametype>")
@try304
def http_export_rating_format_gametype(frmt, gametype):
  frmt = frmt.lower()
  if frmt == "json":
    return jsonify( **rating.export( gametype ) )
  elif frmt == "csv":
    data = rating.export( gametype )
    if data['ok'] == False:
      return "Error: " + data['message'], 400

    result = ""
    
    for row in data["response"]:
      result += ";".join([ row["name"], str(row["rating"]), str(row["n"]), 'http://qlstats.net/player/' + row["_id"] ]) + "\n"

    response = make_response(result)
    response.headers["Content-Disposition"] = "attachment; filename=" + gametype + "_ratings.csv"
    response.headers["Content-Type"]        = "text/csv"
    return response
  else:
    return "Error: invalid format: " + frmt, 400


@app.route("/scoreboard/<match_id>.json")
@try304
def http_scoreboard_match_id_json(match_id):
  try:
    if len(match_id) != len('12345678-1234-5678-1234-567812345678'):
      raise ValueError()
    UUID(match_id)
  except ValueError:
    return jsonify(ok=False, message="invalid match_id")

  return jsonify(**rating.get_scoreboard(match_id))


@app.route("/scoreboard/<match_id>")
@try304
def http_scoreboard_match_id(match_id):
  return render_template("scoreboard.html", match_id = match_id, **rating.get_scoreboard( match_id ))


@app.route("/generate_user_ratings/<gametype>.json")
def http_generate_ratings(gametype):
  return jsonify(**rating.generate_user_ratings(gametype, unquote(request.query_string.decode("utf-8"))))


@app.route("/stats/submit", methods=["POST"])
def http_stats_submit():
  # https://github.com/PredatH0r/XonStat/blob/cfeae1b0c35c48a9f14afa98717c39aa100cde59/feeder/feeder.node.js#L989
  if request.headers.get("X-D0-Blind-Id-Detached-Signature") != "dummy":
    print(request.remote_addr + ": signature header invalid or not found", file=sys.stderr)
    return jsonify(ok=False, message="signature header invalid or not found"), 403

  if request.remote_addr not in ['::ffff:127.0.0.1', '::1', '127.0.0.1']:
    print(request.remote_addr + ": non-loopback requests are not allowed", file=sys.stderr)
    return jsonify(ok=False, message="non-loopback requests are not allowed"), 403

  result = submit_match(request.data.decode('utf-8'))
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

'''
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
