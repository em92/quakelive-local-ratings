#!/usr/bin/env python3

import argparse

from qllr.db import db_connect

parser = argparse.ArgumentParser()
parser.add_argument("steam_id", help="Player's steam_id", type=int)
parser.add_argument("gametype", help="Gametype")
parser.add_argument("r1_mean", help="Mean", type=float)
parser.add_argument("r1_deviation", help="Deviation", type=float)
args = parser.parse_args()

db = db_connect()
cu = db.cursor()

cu.execute(
    "SELECT gametype_id FROM gametypes WHERE gametype_short = %(gametype)s",
    {"gametype": args.gametype},
)
gametype_id = cu.fetchone()[0]

cu.execute(
    """
UPDATE gametype_ratings
SET (r1_mean, r1_deviation) = (%(r1_mean)s, %(r1_deviation)s)
WHERE steam_id = %(steam_id)s AND gametype_id = %(gametype_id)s
""",
    {
        "r1_mean": args.r1_mean,
        "r1_deviation": args.r1_deviation,
        "steam_id": args.steam_id,
        "gametype_id": gametype_id,
    },
)

if cu.rowcount == 0:
    cu.execute(
        "INSERT INTO players (steam_id, name, model, last_played_timestamp) VALUES (%(steam_id)s, '%(steam_id)s', 'sarge/default', 0) ON CONFLICT DO NOTHING",
        {"steam_id": args.steam_id},
    )
    cu.execute(
        "INSERT INTO gametype_ratings (steam_id, gametype_id, n, r1_mean, r1_deviation) VALUES (%(steam_id)s, %(gametype_id)s, 0, %(r1_mean)s, %(r1_deviation)s)",
        {
            "steam_id": args.steam_id,
            "gametype_id": gametype_id,
            "r1_mean": args.r1_mean,
            "r1_deviation": args.r1_deviation,
        },
    )

print("Updated rows", cu.rowcount)
db.commit()
