#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import rating
import requests
import json
import re
from bs4 import BeautifulSoup
import time

# loading qlstatsId -> steamId dictionary
try:
  f = open("s2s.json", "r")
  s2s = json.loads(f.read())
  f.close()
except FileNotFoundError:
  s2s = {}


def get_sec(s):
  l = s.split(':')
  if len(l) == 2:
    l = ['0'] + l
  return int(l[0]) * 3600 + int(l[1]) * 60 + int(l[2])


def download(link):
  print(link)
  try:
    return requests.get(link).text
  except requests.exceptions.ConnectionError:
    return download(link)


def get_steam_id(qlstats_id, ignore_dictionary = False):
  global s2s

  if qlstats_id not in s2s or ignore_dictionary == True:
    html = download("http://qlstats.net/player/" + qlstats_id)
    soup = BeautifulSoup(html, "html.parser")
    s2s[qlstats_id] = soup.select("#xonborder div.row p a")[0].text
    f = open("s2s.json", "w")
    f.write(json.dumps(s2s))
    f.close()

  return s2s[qlstats_id]


def generate_scoreboard(gametype, weapon_data, block, win):
  result = []
  class_to_team = {"grey": '0', "red": '1', "blue": '2'}

  for row in block.select("tbody tr"):
    tds = row.select("td")
    steam_id = get_steam_id(tds[0].find("a")['href'].replace("/player/", ""))
    nickname = tds[0].find("span", class_="nick").text
    result.append( "P " + steam_id )
    result.append( "t " + class_to_team[ row['class'][0] ] )
    result.append( "n " + tds[0].find("span", class_="nick").text )
    result.append( "e alivetime " + str( get_sec(tds[1].text if tds[1].text != "" else '0:00:00') ) )
    result.append( "e playermodel sarge/default" )
    if win:
      result.append( "e wins" )

    scoreboard = {
      'score': tds[6].text if tds[6].text != "" else "0",
      'kills': tds[2].text if tds[2].text != "" else "0",
      'deaths': tds[3].text if tds[3].text != "" else "0",
      'pushes': tds[4].text if tds[4].text != "" else '0',
      'destroyed': tds[5].text if tds[5].text != "" else '0'
    }

    if gametype == "ctf":
      scoreboard['deaths'] = '0'
      scoreboard['pushes'] = tds[6].text if tds[6].text != "" else "0"
      scoreboard['destroyed'] = tds[7].text if tds[7].text != "" else "0"
      scoreboard['score'] = tds[8].text if tds[8].text != "" else "0"

    for name, value in scoreboard.items():
      result.append( "e scoreboard-" + name + " " + value )

    medals = [
      "accuracy",
      #"assists",
      #"captures",
      "combokill",
      #"defends",
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
    for medal in medals:
      result.append( "e medal-" + medal + " 0" )

    if gametype == "ctf":
      result.append( "e medal-captures " + tds[3].text if tds[3].text != "" else "0" )
      result.append( "e medal-assists " + tds[4].text if tds[4].text != "" else "0" )
      result.append( "e medal-defends " + tds[5].text if tds[5].text != "" else "0" )
    else:
      result.append( "e medal-captures 0" )
      result.append( "e medal-assists 0" )
      result.append( "e medal-defends 0" )

    for w, data in weapon_data[ steam_id ].items():
      result.append( "e acc-" + w + "-frags " + data['frags'] )
      result.append( "e acc-" + w + "-cnt-hit " + data['hits'] )
      result.append( "e acc-" + w + "-cnt-fired " + data['shots'] )

  return "\n".join(result)


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
        "hits": str( weapon_data["hits"] ),
        "shots": str( weapon_data["fired"] ),
        "frags": str( weapon_data["kills"] )
      }
    beg += 1
  
  return result


def get_game_results(game_id):
  def get_text_between( temp ):
    temp_start = temp.index("Duration: ") + len("Duration: ")
    temp_end   = temp.index(" ", temp_start)
    return temp[temp_start:temp_end].strip()
    
  result = []
  html = download("http://qlstats.net/game/" + game_id)
  soup = BeautifulSoup(html, "html.parser")
  blocks = soup.select("#xonborder div.row")

  try:
    weapon_stats = get_weapon_stats(soup)
    gametype = blocks[0].find("img")['alt']
    result.append( "I " + blocks[0].select("h2 span.note")[0].text.strip() ) # match_id
    result.append( "M " + blocks[0].select("p a")[1].text.strip().lower() )  # map
    result.append( "G " + gametype )
    result.append( "O " + re.search('\((.*?)\)', blocks[0].select("p")[0].text).group(1) ) # factory
    result.append( "1 " +  blocks[0].select("span.abstime")[0]['data-epoch'] ) # timestamp
    result.append( "D " + str( get_sec( get_text_between( blocks[0].select("p")[0].text ) ) ) ) # duration
    if gametype in ['ad', 'ctf', 'tdm']:
      team_numbers = {'red': '1', 'blue': '2'}
      for team in ['red', 'blue']:
        result.append( 'Q team#' + team_numbers[team] )
        result.append( 'e scoreboard-score ' + soup.select(".teamscore .{}".format( team ))[1].text.strip() )
    result.append( generate_scoreboard(gametype, weapon_stats, blocks[1], True) )
    result.append( generate_scoreboard(gametype, weapon_stats, blocks[2], False) )
  except IndexError:
    print("trying again")
    time.sleep(1)
    return get_game_results(game_id)

  return "\n".join(result)


def main(args):
  global db

  if len(args) < 2 or len(args) > 3:
    print("usage: dump_qlstats_data2.py <server_id> [start_game_id]")
    sys.exit(1)

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
      match_report = get_game_results(game_id)

      print(rating.submit_match(match_report))

    if game_id == None:
      break

    server_results_link = server_results_link_template + "&start_game_id=" + str(int(game_id)-1)

  return 0

if __name__ == '__main__':
  import sys
  if rating.cfg['run_post_process']:
    print("disable run_post_process in cfg.json. exiting...")
    sys.exit(1)
  sys.exit(main(sys.argv))
