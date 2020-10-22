#!/usr/bin/env python3

import argparse
import json
import os
import sys
from datetime import datetime

import requests
from jinja2 import Template

from qllr.db import db_connect
from qllr.settings import TWITCH_CLIENT_ID

DIR = os.path.dirname(os.path.realpath(__file__))
OUTPUT_PATH = DIR + "/../static/vods"

pairs = (
    # ('sergeynixon', 76561198146349598),
    # ('h8m3', 76561197976338965),
    # ('omen812', 76561198256352933),
    # ('p5ych0tr0n', 76561197995121689),
    # ('alostraz', 76561198002370961),
    # ('ch33rra', 76561198292668372),
    # ('Klybi4', 76561198199452077),
    # ('troolzrock', 76561198061282570),
    # ('clawz', 76561198052511951),
    ("madgabz", 76561197972763865),
    ("caretocry", 76561197985202252),
    ("bombaziin", 76561198256292896),
)

db = db_connect()
cu = db.cursor()


def seconds_to_hms(seconds):
    result = ""
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        result += str(h) + "h"
    return result + "{0}m{1}s".format(m, s)


def seconds_to_hms2(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "{0}:{1}:{2}".format(str(h).zfill(2), str(m).zfill(2), str(s).zfill(2))


def get_twitch_videos(account):

    r = requests.get(
        "https://api.twitch.tv/kraken/users?login={0}".format(account),
        headers={
            "Client-ID": TWITCH_CLIENT_ID,
            "Accept": "application/vnd.twitchtv.v5+json",
        },
    )

    data = r.json()

    # fallback if user not found
    if not data["_total"]:
        return {"_total": 0, "videos": []}

    user_id = data["users"][0]["_id"]

    r = requests.get(
        "https://api.twitch.tv/kraken/channels/{0}/videos?limit=100&broadcast_type=archive".format(
            user_id
        ),
        headers={
            "Client-ID": TWITCH_CLIENT_ID,
            "Accept": "application/vnd.twitchtv.v5+json",
        },
    )

    return r.json()


def grab_matches(videos, steam_id):
    for v in videos:
        video_start_timestamp = int(
            datetime.strptime(
                v["recorded_at"] + "+0000", "%Y-%m-%dT%H:%M:%SZ%z"
            ).timestamp()
        )
        video_end_timestamp = video_start_timestamp + v["length"]
        v["recorded_at_timestamp"] = video_start_timestamp
        cu.execute(
            """
SELECT s.match_id, m.timestamp-m.duration, m.duration, mm.map_name
FROM (
    SELECT match_id, steam_id
    FROM scoreboards
    WHERE steam_id = %(steam_id)s
) s
LEFT JOIN matches m ON s.match_id = m.match_id
LEFT JOIN maps mm ON m.map_id = mm.map_id
WHERE
    m.timestamp-m.duration < %(video_end)s AND
    m.timestamp-m.duration > %(video_start)s
ORDER BY m.timestamp ASC
        """,
            {
                "steam_id": steam_id,
                "video_end": video_end_timestamp,
                "video_start": video_start_timestamp,
            },
        )
        v["matches"] = []

        for row in cu.fetchall():
            v["matches"].append(
                {
                    "start_time": row[1] - video_start_timestamp,
                    "map": row[3],
                    "duration": row[2],
                    "match_id": row[0],
                }
            )
        v["matches"].sort(key=lambda v: -v["start_time"])
    videos.sort(key=lambda v: -v["recorded_at_timestamp"])
    return videos


video_entry_template = Template(
    """
<h1>{{ title|e }}</h1>
{% for match in matches %}
    <a href="{{ match.link }}">{{ match.link }}</a> {{ match.mapname }}
    <pre>{{ match.command }}</pre>
    <hr>
{% endfor %}
"""
)

for account, steam_id in pairs:
    result = get_twitch_videos(account)

    if "videos" not in result:
        continue

    with open("{}.html".format(OUTPUT_PATH + "/" + account), "w") as f:
        videos = grab_matches(result["videos"], steam_id)
        for v in videos:
            # from pprint import pprint
            # pprint(v)

            if len(v["matches"]) == 0:
                continue

            entry = video_entry_template.render(
                title=v["title"],
                matches=map(
                    lambda match: {
                        "link": v["url"] + "?t=" + seconds_to_hms(match["start_time"]),
                        "mapname": match["map"],
                        # Thanks to JaySandhu for this:
                        # https://github.com/ytdl-org/youtube-dl/issues/622#issuecomment-162337869
                        "command": "ffmpeg -ss {0} -i `youtube-dl -g {4}` -t {1} -c copy {2}_{3}.mp4".format(
                            seconds_to_hms2(match["start_time"] - 5),
                            seconds_to_hms2(match["duration"] + 60),
                            account,
                            "{}_{}_{}".format(
                                v["_id"], match["map"], match["start_time"]
                            ),
                            v["url"],
                        ),
                    },
                    v["matches"],
                ),
            )

            print(entry, file=f)
