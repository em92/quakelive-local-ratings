#!/usr/bin/env python
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

db = pymongo.MongoClient()['pickup-rating']

f = open("s2s.json", "r")
s2s = json.loads(f.read())
f.close()

def get_sec(s):
	l = s.split(':')
	return int(l[0]) * 3600 + int(l[1]) * 60 + int(l[2])


def download(link):
	print(link)
	return requests.get(link).text


def get_steam_id(qlstats_id):
	global s2s
	
	if qlstats_id not in s2s:
		soup = BeautifulSoup(download("http://qlstats.net/player/" + qlstats_id), "html.parser")
		try:
			s2s[qlstats_id] = soup.select("#xonborder div.row p a")[0].text
		except IndexError:
			time.sleep(1)
			return get_steam_id(qlstats_id)
		f = open("s2s.json", "w")
		f.write(json.dumps(s2s))
		f.close()
	
	return s2s[qlstats_id]
	

def generate_scoreboard(block, win):
	result = []
	for row in block.select("tbody tr"):
		tds = row.select("td")
		result.append({
			'steam-id': get_steam_id(tds[0].find("a")['href'].replace("/player/", "")),
			'score': int(tds[6].text),
			'kills': int(tds[2].text),
			'deaths': int(tds[3].text),
			'damage-dealt': int(tds[4].text),
			'damage-taken': int(tds[5].text),
			'time': get_sec(tds[1].text),
			"win": win
		})
	return result


def get_game_results(game_id):
	result = {}
	soup = BeautifulSoup(download("http://qlstats.net/game/" + game_id), "html.parser")
	blocks = soup.select("#xonborder div.row")
	
	try:
		result['game-id'] = int(game_id)
		result['match-id'] = blocks[0].select("h2 span.note")[0].text.strip()
		result['map'] = blocks[0].select("p a")[1].text.strip().lower()
		result['gametype'] = blocks[0].find("img")['alt']
		result['factory'] = re.search('\((.*?)\)', blocks[0].select("p")[0].text).group(1)
		result['scoreboard'] = generate_scoreboard(blocks[1], True) + generate_scoreboard(blocks[2], False)
	except IndexError:
		time.sleep(1)
		return get_game_results(game_id)
	
	return result

def main(args):
	if len(args) < 2 or len(args) > 3:
		print("usage: dump-qlstats-data <server_id> [start_game_id]")
		return 1
	
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
