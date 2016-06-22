#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import requests
import json
import re
from bs4 import BeautifulSoup
import pymongo
import time

# 798
# 805
# 738

db = None

# loading qlstatsId -> steamId dictionary
try:
  f = open("s2s.json", "r")
  s2s = json.loads(f.read())
  f.close()
except FileNotFoundError:
  s2s = {}


def get_sec(s):
  l = s.split(':')
  return int(l[0]) * 3600 + int(l[1]) * 60 + int(l[2])


def download(link):
  print(link)
  return requests.get(link).text


def get_steam_id(qlstats_id, ignore_dictionary = False):

  def convert_nickname(nickname):
    for i in ["0", "1", "2", "3", "4", "5", "6", "7"]:
      nickname = nickname.replace('<span class="ql' + i + '">', '^' + i)
    return nickname.replace("</span>", "")

  global s2s
  global db

  if qlstats_id not in s2s or ignore_dictionary == True:
    html = download("http://qlstats.net/player/" + qlstats_id)
    soup = BeautifulSoup(html, "html.parser")
    try:
      s2s[qlstats_id] = soup.select("#xonborder div.row p a")[0].text
      db.players.insert_one({
        "_id": s2s[qlstats_id],
        "name": convert_nickname(soup.select("#xonborder div.row h2 span.ql7")[0].decode_contents(formatter="html"))
      })
    except IndexError:
      time.sleep(1)
      return get_steam_id(qlstats_id)
    except pymongo.errors.DuplicateKeyError:
      pass
    f = open("s2s.json", "w")
    f.write(json.dumps(s2s))
    f.close()

  return s2s[qlstats_id]


def generate_scoreboard(gametype, block, win):
  result = []

  for row in block.select("tbody tr"):
    tds = row.select("td")
    item = {
      'steam-id': get_steam_id(tds[0].find("a")['href'].replace("/player/", "")),
      'score': int(tds[6].text if tds[6].text != "" else "0"),
      'kills': int(tds[2].text if tds[2].text != "" else "0"),
      'deaths': int(tds[3].text if tds[3].text != "" else "0"),
      'damage-dealt': int(tds[4].text if tds[4].text != "" else "0"),
      'damage-taken': int(tds[5].text if tds[5].text != "" else "0"),
      'time': get_sec(tds[1].text if tds[1].text != "" else "0:00:00"),
      "win": win
    }
  
    if gametype == "ctf":
      del item['deaths']
      item['damage-dealt'] = int(tds[6].text if tds[6].text != "" else "0")
      item['damage-taken'] = int(tds[7].text if tds[7].text != "" else "0")
      item['score'] = int(tds[8].text if tds[8].text != "" else "0")
  
    result.append(item)
  return result


def get_game_results(game_id, add_scoreboard = True):
  result = {}
  html = download("http://qlstats.net/game/" + game_id)
  soup = BeautifulSoup(html, "html.parser")
  blocks = soup.select("#xonborder div.row")

  try:
    try:
      result['game-id'] = int(game_id)
    except ValueError:
      pass
    result['_id'] = blocks[0].select("h2 span.note")[0].text.strip()
    result['map'] = blocks[0].select("p a")[1].text.strip().lower()
    result['gametype'] = blocks[0].find("img")['alt']
    result['factory'] = re.search('\((.*?)\)', blocks[0].select("p")[0].text).group(1)
    result['timestamp'] = int(blocks[0].select("span.abstime")[0]['data-epoch'])
    if add_scoreboard == True:
      result['scoreboard'] = generate_scoreboard(result['gametype'], blocks[1], True) + generate_scoreboard(result['gametype'], blocks[2], False)
  except IndexError:
    time.sleep(1)
    return get_game_results(game_id)

  return result


def connect_to_database():
  from urllib.parse import urlparse
  
  f = open("cfg.json", "r")
  cfg = json.loads(f.read())
  f.close()

  if "db-url" not in cfg:
    raise ValueError("db-url not found in cfg.json")
  temp = urlparse(cfg['db-url'])

  if temp.scheme != 'mongodb':
    raise ValueError("invalid scheme in db-url (" + temp.scheme + ")")

  if temp.port == None:
    temp.port = 27017

  if any((c in '/\. "$*<>:|?') for c in temp.path[1:]):
    raise ValueError("invalid database name in db-url (" + temp.path[1:] + ")")

  print("server: " + temp.hostname + ":" + str(temp.port))
  print("database: " +temp.path[1:])
  return pymongo.MongoClient(temp.hostname, temp.port)[temp.path[1:]]


def fix_missing_names():
  global db
  global s2s

  cnt = 0
  l = len(s2s.keys())
  for player_id in s2s.keys():
    cnt += 1
    print( str(cnt) + " / " + str(l) )
    if db.players.find_one({"_id": s2s[player_id]}) == None:
      get_steam_id(player_id, True)

  return 0


def main(args):
  global db

  if len(args) < 2 or len(args) > 3:
    print("usage: dump-qlstats-data <server_id> [start_game_id]")
    sys.exit(1)

  try:
    db = connect_to_database()

  except Exception as e:
    print("error: " + str(e))
    return 1

  if args[1] == "fix-missing-names":
    return fix_missing_names()
    
  server_id = args[1]
  server_results_link_template = "http://qlstats.net/games?type=overall&server_id=" + server_id

  if len(args) == 3:
    server_results_link = server_results_link_template + "&start_game_id=" + args[2]
  else:
    server_results_link = server_results_link_template

  while True:
    soup = BeautifulSoup(download(server_results_link), 'html.parser')
    game_id = None
    for btn in soup.select(".btn"):
      game_id = btn['href'].replace("/game/", "")
      game_results = get_game_results(game_id)
      try:
        db.matches.insert_one(game_results)
      except pymongo.errors.DuplicateKeyError:
        print("DuplicateKeyError")

    if game_id == None:
      break

    server_results_link = server_results_link_template + "&start_game_id=" + str(int(game_id)-1)

  return 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv))
