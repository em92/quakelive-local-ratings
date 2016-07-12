#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import requests
import json
import re
from bs4 import BeautifulSoup
import pymongo
import time

GAMETYPES_AVAILABLE = ["ad", "ctf", "ictf", "tdm"]

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


def generate_scoreboard(match_id, gametype, weapon_stats, block, win):
  result = []
  class_to_team = {"grey": 0, "red": 1, "blue": 2}

  for row in block.select("tbody tr"):
    tds = row.select("td")
    item = {
      '_id': {
        'steam_id': get_steam_id(tds[0].find("a")['href'].replace("/player/", "")),
        'match_id': match_id,
        "team": class_to_team[ row['class'] ]
      },
      'score': int(tds[6].text if tds[6].text != "" else "0"),
      'kills': int(tds[2].text if tds[2].text != "" else "0"),
      'deaths': int(tds[3].text if tds[3].text != "" else "0"),
      'damage-dealt': int(tds[4].text if tds[4].text != "" else "0"),
      'damage-taken': int(tds[5].text if tds[5].text != "" else "0"),
      'time': get_sec(tds[1].text if tds[1].text != "" else "0:00:00"),
      "win": win
    }
  
    if gametype == "ctf":
      item['deaths'] = 0
      item['damage-dealt'] = int(tds[6].text if tds[6].text != "" else "0")
      item['damage-taken'] = int(tds[7].text if tds[7].text != "" else "0")
      item['score'] = int(tds[8].text if tds[8].text != "" else "0")
    
    medals = [
      "accuracy",
      "assists",
      "captures",
      "combokill",
      "defends",
      "excellent",
      "firstfrag",
      "headshot",
      "humiliation",
      "impressive",
      "midair",
      "perfect",
      "perforated",
      "quadgod",
      "rampage",
      "revenge"
    ]
    item["medals"] = {}
    for medal in medals:
      item["medals"][medal] = 0

    if gametype == "ctf":
      item["medals"]["captures"] = int(tds[3].text if tds[3].text != "" else "0")
    
    item["weapons"] = weapon_stats[ item["_id"]["steam_id"] ]
    
    result.append(item)
  return result


def is_instagib(soup):
  block = soup.select("#chartRow script")[0].decode_contents(formatter="html")
  weapon_stats_row_count = block.count("var p = weaponStats[i++] = {}")
  assert weapon_stats_row_count != 0
  
  for weapon in ['mg', 'sg', 'gl', 'rl', 'lg', 'pg', 'hmg']:
    weapon_count = block.count("p['" + weapon + "'] = { kills: 0, acc: 0, hits: 0, fired: 0 };")
    if weapon_count != weapon_stats_row_count:
      return False
  
  return True


def get_weapon_stats(soup):
  block = soup.select("#chartRow script")[0].decode_contents(formatter="html")
  steam_ids = map( lambda x: get_steam_id( x['href'].replace("/player/", "") ), soup.select("#accuracyTable a") )
  result = {}
  
  beg = 0
  for steam_id in steam_ids:
    beg = block.index("var p = weaponStats[i++] = {};", beg)
    try:
      end = block.index("var p = weaponStats[i++] = {};", beg+1)
    except:
      end = len(block)-1;
    weapon_block = block[beg:end];
    result[ steam_id ] = {}
    
    for weapon in ['gt', 'mg', 'sg', 'gl', 'rl', 'lg', 'rg', 'pg', 'hmg']:
      beg_str = "p['" + weapon + "'] = "
      end_str = ";"
      beg_index = weapon_block.index(beg_str) + len(beg_str)
      end_index = weapon_block.index(end_str, beg_index)
      weapon_data = weapon_block[beg_index:end_index].replace('kills', '"kills"').replace('hits', '"hits"').replace('fired', '"fired"').replace('acc', '"acc"')
      weapon_data = json.loads( weapon_data )
      result[ steam_id ][ weapon ] = {
        "hits": weapon_data["hits"],
        "shots": weapon_data["fired"],
        "frags": weapon_data["kills"]
      }
    beg += 1
  
  return result


def get_game_results(game_id):
  result = {}
  html = download("http://qlstats.net/game/" + game_id)
  soup = BeautifulSoup(html, "html.parser")
  blocks = soup.select("#xonborder div.row")
  weapon_stats = get_weapon_stats(soup)

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
    scoreboard = generate_scoreboard(result['_id'], result['gametype'], weapon_stats, blocks[1], True) + generate_scoreboard(result['_id'], result['gametype'], weapon_stats, blocks[2], False)
    if is_instagib(soup):
      result['gametype'] = "i" + result['gametype']
    result['is_post_processed'] = False
  except IndexError:
    time.sleep(1)
    return get_game_results(game_id)

  return [result, scoreboard]


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
    print("usage: dump_qlstats_data <server_id> [start_game_id]")
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
    for tr in soup.select("table tbody tr"):
      btn = tr.find("a", class_="btn")
      game_id = btn['href'].replace("/game/", "")
      gametype = tr.find_all("td")[2].text.strip()
      if gametype not in GAMETYPES_AVAILABLE and ("i"+gametype) not in GAMETYPES_AVAILABLE:
        continue
      game_results, scoreboard = get_game_results(game_id)
      try:
        db.matches.insert_one(game_results)
        db.scoreboards.insert_many(scoreboard)
      except pymongo.errors.DuplicateKeyError:
        print("DuplicateKeyError")

    if game_id == None:
      break

    server_results_link = server_results_link_template + "&start_game_id=" + str(int(game_id)-1)

  return 0

if __name__ == '__main__':
  import sys
  sys.exit(main(sys.argv))
