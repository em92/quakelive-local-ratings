from asyncio import Lock
from typing import Optional
from warnings import warn

import trueskill
from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError

from .common import log_exception
from .db import cache, db_connect, get_db_pool
from .exceptions import *
from .gametypes import GAMETYPE_RULES, detect_by_match_report
from .settings import (
    INITIAL_R1_DEVIATION,
    INITIAL_R1_MEAN,
    MIN_PLAYER_COUNT_IN_MATCH_TO_RATE as MIN_PLAYER_COUNT_TO_RATE,
    MOVING_AVG_COUNT,
    RUN_POST_PROCESS,
)

MIN_DURATION_TO_ADD = 60 * 5

lock = Lock()

# https://github.com/PredatH0r/XonStat/blob/380fbd4aeafb722c844f66920fb850a0ad6821d3/xonstat/views/submission.py#L19
def parse_stats_submission(body):
    """
    Parses the POST request body for a stats submission
    """
    # storage vars for the request body
    game_meta = {}
    events = {}
    players = []
    teams = []

    # we're not in either stanza to start
    in_P = in_Q = False

    for line in body.split("\n"):
        try:
            (key, value) = line.strip().split(" ", 1)

            if key not in "P" "Q" "n" "e" "t" "i":
                game_meta[key] = value

            if key == "Q" or key == "P":
                # log.debug('Found a {0}'.format(key))
                # log.debug('in_Q: {0}'.format(in_Q))
                # log.debug('in_P: {0}'.format(in_P))
                # log.debug('events: {0}'.format(events))

                # check where we were before and append events accordingly
                if in_Q and len(events) > 0:
                    # log.debug('creating a team (Q) entry')
                    teams.append(events)
                    events = {}
                elif in_P and len(events) > 0:
                    # log.debug('creating a player (P) entry')
                    players.append(events)
                    events = {}

                if key == "P":
                    # log.debug('key == P')
                    in_P = True
                    in_Q = False
                elif key == "Q":
                    # log.debug('key == Q')
                    in_P = False
                    in_Q = True

                events[key] = value

            if key == "e":
                (subkey, subvalue) = value.split(" ", 1)
                events[subkey] = subvalue
            if key == "n":
                events[key] = value
            if key == "t":
                events[key] = value
        except:
            # no key/value pair - move on to the next line
            pass

    # add the last entity we were working on
    if in_P and len(events) > 0:
        players.append(events)
    elif in_Q and len(events) > 0:
        teams.append(events)

    return {"game_meta": game_meta, "players": players, "teams": teams}


async def get_factory_id(con: Connection, factory: str):
    stmt = await con.prepare(
        "SELECT factory_id FROM factories WHERE factory_short = $1"
    )
    result = await stmt.fetchval(factory)
    if result is None:
        stmt = await con.prepare(
            "INSERT INTO factories (factory_id, factory_short) VALUES (nextval('factory_seq'), $1) RETURNING factory_id"
        )
        result = await stmt.fetchval(factory)

    return result


async def get_map_id(
    con: Connection, map_name: str, create_if_not_exists: bool = True
) -> Optional[int]:
    map_name = map_name.lower()

    stmt = await con.prepare("SELECT map_id FROM maps WHERE map_name = $1")
    result = await stmt.fetchval(map_name)
    if result is None and create_if_not_exists is True:
        stmt = await con.prepare(
            "INSERT INTO maps (map_id, map_name) VALUES (nextval('map_seq'), $1) RETURNING map_id"
        )
        result = await stmt.fetchval(map_name)

    return result


def count_player_match_perf(gametype, player_data, match_duration):
    for k, v in player_data.items():
        if player_data[k] is None:
            player_data[k] = 0

    alive_time = int(player_data["alivetime"])

    if alive_time < match_duration / 2:
        return None
    else:
        time_factor = 1200.0 / alive_time

    return GAMETYPE_RULES[gametype].calc_player_perf(player_data, time_factor)


def count_multiple_players_match_perf(gametype, all_players_data, match_duration):

    result = {}
    temp = []
    sum_perf = 0
    for player in all_players_data:
        team = int(player["t"]) if "t" in player else 0
        steam_id = int(player["P"])
        perf = (
            count_player_match_perf(gametype, player, match_duration)
            if MIN_PLAYER_COUNT_TO_RATE[gametype] <= len(all_players_data)
            else None
        )
        if perf != None:
            temp.append({"team": team, "steam_id": steam_id, "perf": perf})
            sum_perf += perf
        if team not in result:
            result[team] = {}
        result[team][steam_id] = {"perf": perf}

    return result


async def _calc_ratings_avg_perf(
    con: Connection, match_id: str, gametype_id: int, map_id: Optional[int] = None
):
    if map_id is None:
        ratings_subquery = """
            SELECT steam_id, r2_value AS rating
            FROM gametype_ratings
            WHERE gametype_id = $1
        """
        query_params = [gametype_id, match_id]
    else:
        ratings_subquery = """
            SELECT steam_id, r2_value as rating
            FROM map_gametype_ratings
            WHERE gametype_id = $1 AND map_id = $3
        """
        query_params = [gametype_id, match_id, map_id]

    query = """
        SELECT
            s.steam_id,
            team,
            s.match_perf,
            gr.rating
        FROM
            scoreboards s
        LEFT JOIN ({SUBQUERY}) gr ON gr.steam_id = s.steam_id
        WHERE
            match_perf IS NOT NULL AND
            match_id = $2
    """.format(
        SUBQUERY=ratings_subquery
    )

    result = {}

    async for row in con.cursor(query, *query_params):
        steam_id = row[0]
        team = row[1]
        match_perf = row[2]
        old_rating = row[3]

        if old_rating is None:
            new_rating = match_perf
        else:
            query = """
            SELECT
                COUNT(1),
                SUM(win) as wins,
                SUM(loss) as losses,
                AVG(rating)
            FROM (
                SELECT
                    CASE
                        WHEN m.team1_score > m.team2_score AND s.team = 1 THEN 1
                        WHEN m.team2_score > m.team1_score AND s.team = 2 THEN 1
                        ELSE 0
                    END as win,
                    CASE
                        WHEN m.team1_score > m.team2_score AND s.team = 1 THEN 0
                        WHEN m.team2_score > m.team1_score AND s.team = 2 THEN 0
                        ELSE 1
                    END as loss,
                    s.match_perf as rating
                FROM
                    matches m
                LEFT JOIN
                    scoreboards s on s.match_id = m.match_id
                WHERE
                    s.steam_id = $1 AND
                    m.gametype_id = $2 AND
                    (m.post_processed = TRUE OR m.match_id = $3) AND
                    s.match_perf IS NOT NULL
                ORDER BY m.timestamp DESC
                LIMIT {MOVING_AVG_COUNT}
            ) t""".format(
                MOVING_AVG_COUNT=MOVING_AVG_COUNT
            )

            row = await con.fetchrow(query, steam_id, gametype_id, match_id)
            gametype = [k for k, v in cache.GAMETYPE_IDS.items() if v == gametype_id][0]
            rules = GAMETYPE_RULES[gametype]
            new_rating = row[3] * rules.extra_factor(row[0], row[1], row[2])

        result[steam_id] = {"old": old_rating, "new": new_rating, "team": team}

    return result


async def _calc_ratings_trueskill(
    con: Connection, match_id: str, gametype_id: int, map_id: Optional[int] = None
):
    gametype = [k for k, v in cache.GAMETYPE_IDS.items() if v == gametype_id][0]

    row = await con.fetchrow(
        "SELECT team2_score > team1_score, team2_score < team1_score FROM matches WHERE match_id = $1",
        match_id,
    )
    team_ranks = [row[0], row[1]]

    if map_id is None:
        ratings_subquery = """
            SELECT steam_id, r1_mean AS mean, r1_deviation AS deviation
            FROM gametype_ratings
            WHERE gametype_id = $1
        """
        query_params = [gametype_id, match_id]
    else:
        ratings_subquery = """
            SELECT steam_id, r1_mean AS mean, r1_deviation AS deviation
            FROM map_gametype_ratings
            WHERE gametype_id = $1 AND map_id = $3
        """
        query_params = [gametype_id, match_id, map_id]

    rows = await con.fetch(
        """
        SELECT
            s.steam_id,
            team,
            s.match_perf,
            gr.mean,
            gr.deviation
        FROM
            scoreboards s
        LEFT JOIN ({SUBQUERY}) gr ON gr.steam_id = s.steam_id
        WHERE
            match_perf IS NOT NULL AND
            match_id = $2
        """.format(
            SUBQUERY=ratings_subquery
        ),
        *query_params
    )

    team_ratings_old = [[], []]
    team_ratings_new = [[], []]
    team_steam_ids = [[], []]
    for row in rows:
        steam_id = row[0]
        team = row[1]
        # match_perf   = row[2]
        mean = row[3]
        deviation = row[4]

        if mean is None:
            mean = INITIAL_R1_MEAN[gametype]
        if deviation is None:
            deviation = INITIAL_R1_DEVIATION[gametype]
        ts_rating = trueskill.Rating(mean, deviation)

        try:
            team_ratings_old[team - 1].append(ts_rating)
            team_steam_ids[team - 1].append(steam_id)
        except KeyError:
            continue

    if len(team_ratings_old[0]) == 0 or len(team_ratings_old[1]) == 0:
        return

    team1_ratings, team2_ratings = trueskill.rate(team_ratings_old, ranks=team_ranks)

    steam_ids = team_steam_ids[0] + team_steam_ids[1]
    new_ratings = team1_ratings + team2_ratings
    old_ratings = team_ratings_old[0] + team_ratings_old[1]

    assert len(steam_ids) == len(new_ratings) == len(old_ratings)

    steam_ratings = {}
    for i in range(len(steam_ids)):
        steam_id = steam_ids[i]

        if steam_id in steam_ratings:  # player played for both teams. Ignoring...
            del steam_ratings[steam_id]

        steam_ratings[steam_id] = {
            "old": old_ratings[i],
            "new": new_ratings[i],
            "team": 1 if i < len(team1_ratings) else 2,
        }

    return steam_ratings


async def _post_process(
    con: Connection, match_id: str, gametype_id: int, match_timestamp: int
):
    """
    Updates players' ratings after playing match_id

    """
    trueskill_ratings = await _calc_ratings_trueskill(con, match_id, gametype_id)
    if trueskill_ratings is None:
        return

    avg_perf_ratings = await _calc_ratings_avg_perf(con, match_id, gametype_id)

    for steam_id, ratings in trueskill_ratings.items():
        r = await con.execute(
            """
            UPDATE scoreboards
            SET
                old_r1_mean = $1, old_r1_deviation = $2,
                new_r1_mean = $3, new_r1_deviation = $4,
                old_r2_value = $5, new_r2_value = $6
            WHERE match_id = $7 AND steam_id = $8 AND team = $9
            """,
            ratings["old"].mu,
            ratings["old"].sigma,
            ratings["new"].mu,
            ratings["new"].sigma,
            avg_perf_ratings[steam_id]["old"],
            avg_perf_ratings[steam_id]["new"],
            match_id,
            steam_id,
            ratings["team"],
        )
        assert r == "UPDATE 1"

        r = await con.execute(
            """
            UPDATE gametype_ratings
            SET r1_mean = $1, r1_deviation = $2, r2_value = $3, n = n + 1, last_played_timestamp = $4
            WHERE steam_id = $5 AND gametype_id = $6
            """,
            ratings["new"].mu,
            ratings["new"].sigma,
            avg_perf_ratings[steam_id]["new"],
            match_timestamp,
            steam_id,
            gametype_id,
        )

        if r == "UPDATE 0":
            r = await con.execute(
                """
                INSERT INTO gametype_ratings (steam_id, gametype_id, r1_mean, r1_deviation, r2_value, last_played_timestamp, n)
                VALUES ($1, $2, $3, $4, $5, $6, 1)
                """,
                steam_id,
                gametype_id,
                ratings["new"].mu,
                ratings["new"].sigma,
                avg_perf_ratings[steam_id]["new"],
                match_timestamp,
            )
        assert r == "UPDATE 1" or r == "INSERT 0 1"


async def update_map_rating(
    con: Connection, match_id: str, gametype_id: int, match_timestamp: int, map_id: int
):
    """
    Updates players' map-based ratings after playing match_id

    """
    trueskill_ratings = await _calc_ratings_trueskill(
        con, match_id, gametype_id, map_id
    )
    if trueskill_ratings is None:
        return

    avg_perf_ratings = await _calc_ratings_avg_perf(con, match_id, gametype_id, map_id)

    for steam_id, ratings in trueskill_ratings.items():
        r = await con.execute(
            """
            UPDATE map_gametype_ratings
            SET r1_mean = $1, r1_deviation = $2, n = n + 1, last_played_timestamp = $3
            WHERE steam_id = $4 AND gametype_id = $5 AND map_id = $6
            """,
            ratings["new"].mu,
            ratings["new"].sigma,
            match_timestamp,
            steam_id,
            gametype_id,
            map_id,
        )

        if r == "UPDATE 0":
            r = await con.execute(
                """
                INSERT INTO map_gametype_ratings (steam_id, gametype_id, map_id, r1_mean, r1_deviation, r2_value, last_played_timestamp, n)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 1)
                """,
                steam_id,
                gametype_id,
                map_id,
                ratings["new"].mu,
                ratings["new"].sigma,
                avg_perf_ratings[steam_id]["new"],
                match_timestamp,
            )
        assert r == "UPDATE 1" or r == "INSERT 0 1"


async def post_process(
    con: Connection, match_id: str, gametype_id: int, match_timestamp: int, map_id: int
):
    await _post_process(con, match_id, gametype_id, match_timestamp)
    await update_map_rating(con, match_id, gametype_id, match_timestamp, map_id)

    r = await con.execute(
        "UPDATE matches SET post_processed = TRUE WHERE match_id = $1", match_id
    )
    assert r == "UPDATE 1"

    cache.LAST_GAME_TIMESTAMPS[gametype_id] = match_timestamp


def filter_insignificant_players(players):
    return list(filter(lambda player: int(player["scoreboard-destroyed"]) > 0, players))


async def submit_match(data):
    async with lock:
        return await _submit_match(data)


async def _submit_match(data):
    """
    Match report handler

    Args:
        data (str): match report

    Returns: {
        "message":      - operation result description
        "match_id":     - match_id of match_report
    }
    """
    if type(data).__name__ == "str":
        data = parse_stats_submission(data)
    elif "players" not in data:
        raise InvalidMatchReport("No player data")
    elif "game_meta" not in data:
        raise InvalidMatchReport("No game meta data")

    data["players"] = filter_insignificant_players(data["players"])

    try:
        match_id = data["game_meta"]["I"]
    except KeyError:
        raise InvalidMatchReport("Match id not given")

    try:
        gametype = detect_by_match_report(data)
    except KeyError:
        raise InvalidMatchReport("Gametype not given")

    if gametype not in cache.GAMETYPE_IDS:
        raise InvalidMatchReport("Gametype not accepted: {}".format(gametype))

    try:
        match_duration = int(data["game_meta"]["D"])
    except KeyError:
        raise InvalidMatchReport("Match duration not given")
    except ValueError:
        raise InvalidMatchReport(
            "Match duration is not integer: {}".format(data["game_meta"]["D"])
        )

    if match_duration < MIN_DURATION_TO_ADD:
        raise InvalidMatchReport(
            "not enough match duration: given - {}, required - {}".format(
                match_duration, MIN_DURATION_TO_ADD
            )
        )

    dbpool = await get_db_pool()
    con = await dbpool.acquire()
    tr = con.transaction()
    await tr.start()

    try:
        team_scores = [None, None]
        team_index = -1
        for team_data in data["teams"]:
            team_index = int(team_data["Q"].replace("team#", "")) - 1
            for key in ["scoreboard-rounds", "scoreboard-caps", "scoreboard-score"]:
                if key in team_data:
                    team_scores[team_index] = int(team_data[key])
        team1_score, team2_score = team_scores

        match_timestamp = int(data["game_meta"]["1"])
        map_id = await get_map_id(con, data["game_meta"]["M"])
        try:
            await con.execute(
                "INSERT INTO matches (match_id, gametype_id, factory_id, map_id, timestamp, duration, team1_score, team2_score, post_processed) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                match_id,
                cache.GAMETYPE_IDS[gametype],
                await get_factory_id(con, data["game_meta"]["O"]),
                map_id,
                match_timestamp,
                match_duration,
                team1_score,
                team2_score,
                RUN_POST_PROCESS,
            )
        except UniqueViolationError:
            raise MatchAlreadyExists(match_id)

        player_match_ratings = count_multiple_players_match_perf(
            gametype, data["players"], match_duration
        )
        for player in data["players"]:
            player["P"] = int(player["P"])
            if "playermodel" not in player:
                player["playermodel"] = "sarge/default"
            team = int(player["t"]) if "t" in player else 0

            await con.execute(
                """
                INSERT INTO players (
                    steam_id,
                    name,
                    model,
                    last_played_timestamp
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (steam_id) DO UPDATE SET (name, model, last_played_timestamp) = ($2, $3, $4)
                WHERE players.last_played_timestamp < $4
                """,
                player["P"],
                player["n"],
                player["playermodel"],
                match_timestamp,
            )

            await con.execute(
                """
                INSERT INTO scoreboards (
                    match_id,
                    steam_id,
                    frags,
                    deaths,
                    damage_dealt,
                    damage_taken,
                    score,
                    match_perf,
                    alive_time,
                    team
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """,
                match_id,
                player["P"],
                int(player["scoreboard-kills"]),
                int(player["scoreboard-deaths"]),
                int(player["scoreboard-pushes"]),
                int(player["scoreboard-destroyed"]),
                int(player["scoreboard-score"]),
                player_match_ratings[team][player["P"]]["perf"],
                int(player["alivetime"]),
                team,
            )

            for weapon, weapon_id in cache.WEAPON_IDS.items():
                frags = int(player["acc-" + weapon + "-frags"])
                shots = int(player["acc-" + weapon + "-cnt-fired"])
                if frags + shots == 0:
                    continue

                await con.execute(
                    """
                    INSERT INTO scoreboards_weapons (match_id, steam_id, team, weapon_id, frags, hits, shots, damage_dealt, damage_taken)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    match_id,
                    player["P"],
                    team,
                    weapon_id,
                    frags,
                    int(player["acc-" + weapon + "-cnt-hit"]),
                    shots,
                    int(player["acc-" + weapon + "-fired"]),
                    int(player["acc-" + weapon + "-hit"]),
                )

            for medal, medal_id in cache.MEDAL_IDS.items():
                medal_count = int(player["medal-" + medal])
                if medal_count == 0:
                    continue

                await con.execute(
                    """
                    INSERT INTO scoreboards_medals (match_id, steam_id, team, medal_id, count)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    match_id,
                    player["P"],
                    team,
                    medal_id,
                    medal_count,
                )

        # post processing
        if RUN_POST_PROCESS:
            await post_process(
                con, match_id, cache.GAMETYPE_IDS[gametype], match_timestamp, map_id
            )
            result = {"message": "done", "match_id": match_id}
        else:
            result = {
                "message": "skipped post processing",
                "match_id": match_id,
            }

    except:
        await tr.rollback()
        raise
    else:
        await tr.commit()
    finally:
        await dbpool.release(con)

    return result


async def run_post_process(con: Connection) -> None:
    async with lock:
        await _run_post_process(con)


async def _run_post_process(con: Connection) -> None:
    query = """
        SELECT match_id, gametype_id, timestamp, map_id
        FROM matches
        WHERE post_processed = FALSE
        ORDER BY timestamp ASC
    """
    for match_id, gametype_id, timestamp, map_id in await con.fetch(query):
        print("running post process: {}\t{}".format(match_id, timestamp))
        await post_process(con, match_id, gametype_id, timestamp, map_id)
        await con.execute("COMMIT")
