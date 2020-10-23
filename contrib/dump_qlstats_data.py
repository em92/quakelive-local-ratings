#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

import gzip
import json
import time
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
from pytz import timezone


def get_sec(s):
    l = s.split(":")
    return int(l[0]) * 3600 + int(l[1]) * 60 + int(l[2])


def download(link):
    r = requests.get(link)
    print(link)
    return r.text


def download_stats(match_id, timestamp, path="./"):
    uttz = timezone("UTC")
    vitz = timezone("Europe/Vienna")
    d = datetime.fromtimestamp(timestamp, tz=uttz).replace(tzinfo=uttz).astimezone(vitz)
    link = (
        "https://api.qlstats.net/api/jsons/"
        + str(d.year)
        + "-"
        + str(d.month).zfill(2)
        + "-"
        + str(d.day).zfill(2)
        + "/"
        + match_id
        + ".json"
    )
    data = download(link)
    f = gzip.open(path + match_id + ".json.gz", "wb")
    f.write(data.encode("utf-8"))
    f.close()
    data = json.loads(data)
    try:
        if data["ok"] == False:
            raise Exception("something is wrong")
    except KeyError:
        pass


def get_game_results(game_id):
    result = {}
    html = download("http://qlstats.net/game/" + game_id)
    soup = BeautifulSoup(html, "html.parser")
    download_stats(
        soup.select("#xonborder .game-detail .note")[0].text.strip(),
        int(soup.select("#xonborder .game-detail .abstime")[0]["data-epoch"]),
    )


def main(args):
    if len(args) < 2 or len(args) > 3:
        print("usage: dump_qlstats_data <server_id> [start_game_id]")
        sys.exit(1)

    server_id = args[1]
    server_results_link_template = (
        "http://qlstats.net/games?type=overall&server_id=" + server_id
    )

    if len(args) == 3:
        server_results_link = server_results_link_template + "&start_game_id=" + args[2]
    else:
        server_results_link = server_results_link_template

    while True:
        soup = BeautifulSoup(download(server_results_link), "html.parser")
        game_id = None
        for tr in soup.select("table tbody tr"):
            btn = tr.find("a", class_="btn")
            game_id = btn["href"].replace("/game/", "")
            get_game_results(game_id)

        if game_id == None:
            break

        server_results_link = (
            server_results_link_template + "&start_game_id=" + str(int(game_id) - 1)
        )

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main(sys.argv))
