#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

import trueskill

from qllr.db import db_connect
from qllr.submission import count_multiple_players_match_perf

parser = argparse.ArgumentParser()
parser.add_argument("gametype")
args = parser.parse_args()

from qllr.db import cache

GAMETYPE_IDS = cache.GAMETYPE_IDS


def reset_gametype_ratings(gametype: str) -> int:
    """
    Resets ratings for gametype
    """
    if gametype not in GAMETYPE_IDS:
        print("gametype is not accepted: " + gametype)
        return 1

    gametype_id = GAMETYPE_IDS[gametype]
    result = 1
    try:
        db = db_connect()
        cu = db.cursor()
        cw = db.cursor()

        cw.execute(
            "UPDATE matches SET post_processed = FALSE WHERE gametype_id = %s",
            [gametype_id],
        )
        cw.execute(
            "UPDATE gametype_ratings SET mean = %s, deviation = %s, n = 0 WHERE gametype_id = %s",
            [trueskill.MU, trueskill.SIGMA, gametype_id],
        )
        scoreboard_query = """
        SELECT
      s.match_id,
      MIN(m.team1_score) AS team1_score,
      MIN(m.team2_score) AS team1_score,
      array_agg(json_build_object(
        'P',                    s.steam_id,
        't',                    s.team,
        'alivetime',            s.alive_time,
        'scoreboard-score',     s.score,
        'scoreboard-pushes',    s.damage_dealt,
        'scoreboard-destroyed', s.damage_taken,
        'scoreboard-kills',     s.frags,
        'scoreboard-deaths',    s.deaths,
        'medal-captures',       mm.medals->'captures',
        'medal-defends',        mm.medals->'defends',
        'medal-assists',        mm.medals->'assists'
      )),
      MIN(m.duration)
    FROM
      scoreboards s
    LEFT JOIN matches m ON m.match_id = s.match_id
    LEFT JOIN (
      SELECT
        sm.steam_id, sm.team, sm.match_id,
        json_object_agg(mm.medal_short, sm.count) as medals
      FROM
        scoreboards_medals sm
      LEFT JOIN
        medals mm ON mm.medal_id = sm.medal_id
      GROUP BY sm.steam_id, sm.team, sm.match_id
    ) mm ON mm.match_id = s.match_id AND s.steam_id = mm.steam_id AND s.team = mm.team
    WHERE gametype_id = %s
    GROUP BY s.match_id;
    """

        cu.execute(scoreboard_query, [gametype_id])
        for row in cu:
            match_id = row[0]
            team1_score = row[1]
            team2_score = row[2]
            match_duration = row[4]
            all_players_data = []
            for player in row[3]:
                if player["t"] == 1 and team1_score > team2_score:
                    player["win"] = 1
                if player["t"] == 2 and team1_score < team2_score:
                    player["win"] = 1
                all_players_data.append(player.copy())
            print(match_id)
            player_match_ratings = count_multiple_players_match_perf(
                gametype, all_players_data, match_duration
            )

            for player in all_players_data:
                player["P"] = int(player["P"])
                team = int(player["t"]) if "t" in player else 0

                cw.execute(
                    "UPDATE scoreboards SET match_perf = %s, new_mean = NULL, old_mean = NULL, new_deviation = NULL, old_deviation = NULL WHERE match_id = %s AND team = %s AND steam_id = %s",
                    [
                        player_match_ratings[team][player["P"]]["perf"],
                        match_id,
                        team,
                        player["P"],
                    ],
                )

        db.commit()
        result = 0

    except:
        db.rollback()
    finally:
        cu.close()
        db.close()

    return result


if __name__ == "__main__":
    sys.exit(reset_gametype_ratings(args.gametype))
