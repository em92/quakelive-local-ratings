# -*- coding: utf-8 -*-

from asyncio import Lock
from typing import Optional
from warnings import warn

import trueskill
from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError

from .common import log_exception
from .db import cache, db_connect, get_db_pool
from .exceptions import *
from .settings import MIN_PLAYER_COUNT_IN_MATCH_TO_RATE as MIN_PLAYER_COUNT_TO_RATE
from .settings import MOVING_AVG_COUNT, RUN_POST_PROCESS, USE_AVG_PERF

GAMETYPE_IDS = cache.GAMETYPE_IDS
LAST_GAME_TIMESTAMPS = cache.LAST_GAME_TIMESTAMPS
MEDAL_IDS = cache.MEDAL_IDS
MIN_DURATION_TO_ADD = 60 * 5
WEAPON_IDS = cache.WEAPON_IDS

lock = Lock()

for gt, id in GAMETYPE_IDS.items():
    USE_AVG_PERF[id] = USE_AVG_PERF[gt]


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


def is_tdm2v2(data):
    return data["game_meta"]["G"] == "tdm" and len(data["players"]) == 4


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
    score = int(player_data["scoreboard-score"])
    damage_dealt = int(player_data["scoreboard-pushes"])
    damage_taken = int(player_data["scoreboard-destroyed"])
    frags_count = int(player_data["scoreboard-kills"])
    deaths_count = int(player_data["scoreboard-deaths"])
    capture_count = int(player_data["medal-captures"])
    defends_count = int(player_data["medal-defends"])
    assists_count = int(player_data["medal-assists"])
    win = 1 if "win" in player_data else 0

    if alive_time < match_duration / 2:
        return None
    else:
        time_factor = 1200.0 / alive_time

    return {
        "ad": (damage_dealt / 100 + frags_count + capture_count) * time_factor,
        "ca": (damage_dealt / 100 + 0.25 * frags_count) * time_factor,
        "ctf": (damage_dealt / damage_taken * (score + damage_dealt / 20) * time_factor)
        / 2.35
        + win * 300,
        "ft": (
            damage_dealt / 100 + 0.5 * (frags_count - deaths_count) + 2 * assists_count
        )
        * time_factor,
        "tdm2v2": (
            0.5 * (frags_count - deaths_count)
            + 0.004 * (damage_dealt - damage_taken)
            + 0.003 * damage_dealt
        )
        * time_factor,
        "tdm": (
            0.5 * (frags_count - deaths_count)
            + 0.004 * (damage_dealt - damage_taken)
            + 0.003 * damage_dealt
        )
        * time_factor,
    }[gametype]


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


async def post_process_avg_perf(
    con: Connection, match_id: str, gametype_id: int, match_timestamp: int
):
    """
    Updates players' ratings after playing match_id (using avg. perfomance)

    """

    def extra_factor(gametype, matches, wins, losses):
        try:
            return {"tdm": (1 + (0.15 * (wins / matches - losses / matches)))}[gametype]
        except KeyError:
            return 1

    global LAST_GAME_TIMESTAMPS
    query = """
    SELECT s.steam_id, team, match_perf, gr.mean
    FROM scoreboards s
    LEFT JOIN gametype_ratings gr ON gr.steam_id = s.steam_id AND gr.gametype_id = $1
    WHERE match_perf IS NOT NULL AND match_id = $2
    """

    async for row in con.cursor(query, gametype_id, match_id):
        steam_id = row[0]
        team = row[1]
        match_perf = row[2]
        old_rating = row[3]

        query = """
        UPDATE scoreboards
        SET old_mean = $1, old_deviation = 0
        WHERE match_id = $2 AND steam_id = $3 AND team = $4
        """
        rowcount = await con.execute(query, old_rating, match_id, steam_id, team)
        assert rowcount == "UPDATE 1"

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
            gametype = [k for k, v in GAMETYPE_IDS.items() if v == gametype_id][0]
            new_rating = row[3] * extra_factor(gametype, row[0], row[1], row[2])

        query = """
        UPDATE scoreboards
        SET new_mean = $1, new_deviation = 0
        WHERE match_id = $2 AND steam_id = $3 AND team = $4
        """
        rowcount = await con.execute(query, new_rating, match_id, steam_id, team)
        assert rowcount == "UPDATE 1"

        query = """
        UPDATE gametype_ratings
        SET mean = $1, deviation = 0, n = n + 1, last_played_timestamp = $2
        WHERE steam_id = $3 AND gametype_id = $4
        """
        rowcount = await con.execute(
            query, new_rating, match_timestamp, steam_id, gametype_id
        )
        if rowcount == "UPDATE 0":
            query = """
            INSERT INTO gametype_ratings
            (steam_id, gametype_id, mean, deviation, last_played_timestamp, n)
            VALUES
            ($1, $2, $3, 0, $4, 1)
            """
            rowcount = await con.execute(
                query, steam_id, gametype_id, new_rating, match_timestamp
            )
            assert rowcount == "INSERT 0 1"
        else:
            assert rowcount == "UPDATE 1"


async def post_process_trueskill(
    con: Connection, match_id: str, gametype_id: int, match_timestamp: int
):
    """
    Updates players' ratings after playing match_id (using trueskill)

    """
    global LAST_GAME_TIMESTAMPS
    row = await con.fetchrow(
        "SELECT team2_score > team1_score, team2_score < team1_score FROM matches WHERE match_id = $1",
        match_id,
    )
    team_ranks = [row[0], row[1]]

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
        LEFT JOIN (
            SELECT steam_id, mean, deviation
            FROM gametype_ratings
            WHERE gametype_id = $1
            ) gr ON gr.steam_id = s.steam_id
        WHERE
            match_perf IS NOT NULL AND
            match_id = $2
        """,
        gametype_id,
        match_id,
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

        try:
            ts_rating = trueskill.Rating(mean, deviation)
            # TODO: надо это переписать так, чтобы можно было записать оба вида рейтинга
            # TODO: И если по какой-то причине тут выкидывается исключение - используй рейтинг по-умолчанию, а ниже - не ворнинг а вывод в sys.stderr
        except ValueError as e:
            warn(
                "Cannot use trueskill rating: {}. Falling back to average perfomance rating...".format(
                    e
                )
            )
            return await post_process_avg_perf(con, match_id, gametype_id, match_timestamp)

        try:
            team_ratings_old[team - 1].append(ts_rating)
            team_steam_ids[team - 1].append(steam_id)
        except KeyError:
            continue

    if len(team_ratings_old[0]) == 0 or len(team_ratings_old[1]) == 0:
        return

    team1_ratings, team2_ratings = trueskill.rate(team_ratings_old, ranks=team_ranks)
    team_ratings_new = [team1_ratings, team2_ratings]

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

    for steam_id, ratings in steam_ratings.items():
        r = await con.execute(
            """
            UPDATE scoreboards
            SET
                old_mean = $1, old_deviation = $2,
                new_mean = $3, new_deviation = $4
            WHERE match_id = $5 AND steam_id = $6 AND team = $7
            """,
            ratings["old"].mu,
            ratings["old"].sigma,
            ratings["new"].mu,
            ratings["new"].sigma,
            match_id,
            steam_id,
            ratings["team"],
        )
        assert r == "UPDATE 1"

        r = await con.execute(
            """
            UPDATE gametype_ratings
            SET mean = $1, deviation = $2, n = n + 1, last_played_timestamp = $3
            WHERE steam_id = $4 AND gametype_id = $5
            """,
            ratings["new"].mu,
            ratings["new"].sigma,
            match_timestamp,
            steam_id,
            gametype_id,
        )

        if r == "UPDATE 0":
            r = await con.execute(
                """
                INSERT INTO gametype_ratings (steam_id, gametype_id, mean, deviation, last_played_timestamp, n)
                VALUES ($1, $2, $3, $4, $5, 1)
                """,
                steam_id,
                gametype_id,
                ratings["new"].mu,
                ratings["new"].sigma,
                match_timestamp,
            )
        assert r == "UPDATE 1" or r == "INSERT 0 1"


async def post_process(
    con: Connection, match_id: str, gametype_id: int, match_timestamp: int
):
    if USE_AVG_PERF[gametype_id]:
        await post_process_avg_perf(con, match_id, gametype_id, match_timestamp)
    else:
        await post_process_trueskill(con, match_id, gametype_id, match_timestamp)

    r = await con.execute(
        "UPDATE matches SET post_processed = TRUE WHERE match_id = $1", match_id
    )
    assert r == "UPDATE 1"

    LAST_GAME_TIMESTAMPS[gametype_id] = match_timestamp


def filter_insignificant_players(players):
    return list(filter(lambda player: int(player["scoreboard-destroyed"]) > 0, players))


async def submit_match(data):
    with await lock:
        return await _submit_match(data)


async def _submit_match(data):
    """
    Match report handler

    Args:
        data (str): match report

    Returns: {
        "ok: True/False - on success/fail
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
        gametype = data["game_meta"]["G"]
    except KeyError:
        raise InvalidMatchReport("Gametype not given")

    if is_tdm2v2(data):
        gametype = "tdm2v2"

    if gametype not in GAMETYPE_IDS:
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
        try:
            await con.execute(
                "INSERT INTO matches (match_id, gametype_id, factory_id, map_id, timestamp, duration, team1_score, team2_score, post_processed) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                match_id,
                GAMETYPE_IDS[gametype],
                await get_factory_id(con, data["game_meta"]["O"]),
                await get_map_id(con, data["game_meta"]["M"]),
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

            for weapon, weapon_id in WEAPON_IDS.items():
                frags = int(player["acc-" + weapon + "-frags"])
                shots = int(player["acc-" + weapon + "-cnt-fired"])
                if frags + shots == 0:
                    continue

                await con.execute(
                    """
                    INSERT INTO scoreboards_weapons (match_id, steam_id, team, weapon_id, frags, hits, shots)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    match_id,
                    player["P"],
                    team,
                    weapon_id,
                    frags,
                    int(player["acc-" + weapon + "-cnt-hit"]),
                    shots,
                )

            for medal, medal_id in MEDAL_IDS.items():
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
                con, match_id, GAMETYPE_IDS[gametype], match_timestamp
            )
            result = {"ok": True, "message": "done", "match_id": match_id}
        else:
            result = {
                "ok": True,
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
    with await lock:
        await _run_post_process(con)


async def _run_post_process(con: Connection) -> None:
    query = """
        SELECT match_id, gametype_id, timestamp
        FROM matches
        WHERE post_processed = FALSE
        ORDER BY timestamp ASC
    """
    async for match_id, gametype_id, timestamp in con.cursor(query):
        print("running post process: {}\t{}".format(match_id, timestamp))
        await post_process(con, match_id, gametype_id, timestamp)
