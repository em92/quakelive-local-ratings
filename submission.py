# -*- coding: utf-8 -*-

import trueskill

from common import log_exception
from conf import settings as cfg
from db import db_connect, cache

GAMETYPE_IDS              = cache.GAMETYPE_IDS
LAST_GAME_TIMESTAMPS      = cache.LAST_GAME_TIMESTAMPS
MEDAL_IDS                 = cache.MEDAL_IDS
MIN_ALIVE_TIME_TO_RATE    = 60*10
MIN_PLAYER_COUNT_TO_RATE  = cfg.MIN_PLAYER_COUNT_TO_RATE
MOVING_AVG_COUNT          = cfg['moving_average_count']
USE_AVG_PERF              = cfg.USE_AVG_PERF
WEAPON_IDS                = cache.WEAPON_IDS

for gt, id in GAMETYPE_IDS.items():
  USE_AVG_PERF[ id ] = USE_AVG_PERF[ gt ]


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

  for line in body.split('\n'):
    try:
      (key, value) = line.strip().split(' ', 1)

      if key not in 'P' 'Q' 'n' 'e' 't' 'i':
        game_meta[key] = value

      if key == 'Q' or key == 'P':
        #log.debug('Found a {0}'.format(key))
        #log.debug('in_Q: {0}'.format(in_Q))
        #log.debug('in_P: {0}'.format(in_P))
        #log.debug('events: {0}'.format(events))

        # check where we were before and append events accordingly
        if in_Q and len(events) > 0:
          #log.debug('creating a team (Q) entry')
          teams.append(events)
          events = {}
        elif in_P and len(events) > 0:
          #log.debug('creating a player (P) entry')
          players.append(events)
          events = {}

        if key == 'P':
          #log.debug('key == P')
          in_P = True
          in_Q = False
        elif key == 'Q':
          #log.debug('key == Q')
          in_P = False
          in_Q = True

        events[key] = value

      if key == 'e':
        (subkey, subvalue) = value.split(' ', 1)
        events[subkey] = subvalue
      if key == 'n':
        events[key] = value
      if key == 't':
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


def is_instagib(data):
  '''
  Checks if match is played with instagib mode
  '''
  def is_player_using_weapon( player, weapon ):
    try:
      return True if player['acc-' + weapon + '-cnt-fired'] == '0' else False
    except KeyError:
      return True 

  def is_player_using_railgun_and_gauntlet_only( player ):
    return all( map( lambda weapon: is_player_using_weapon( player, weapon), ['mg', 'sg', 'gl', 'rl', 'lg', 'pg', 'hmg', 'bfg', 'cg', 'ng', 'pm', 'gh'] ) )

  return all( map ( lambda player: is_player_using_railgun_and_gauntlet_only( player ), data['players'] ) )


def is_tdm2v2(data):
  return data["game_meta"]["G"] == "tdm" and len(data["players"]) == 4


def get_factory_id( cu, factory ):
  cu.execute( "SELECT factory_id FROM factories WHERE factory_short = %s", [factory] )
  try:
    return cu.fetchone()[0]
  except TypeError:
    cu.execute("INSERT INTO factories (factory_id, factory_short) VALUES (nextval('factory_seq'), %s) RETURNING factory_id", [factory])
    return cu.fetchone()[0]


def get_map_id( cu, map_name, dont_create = False ):
  map_name = map_name.lower()
  cu.execute( "SELECT map_id FROM maps WHERE map_name = %s", [map_name] )
  try:
    return cu.fetchone()[0]
  except TypeError:
    if dont_create:
      return None
    cu.execute("INSERT INTO maps (map_id, map_name) VALUES (nextval('map_seq'), %s) RETURNING map_id", [map_name])
    return cu.fetchone()[0]


def count_player_match_perf( gametype, player_data ):
  alive_time    = int( player_data["alivetime"] )
  score         = int( player_data["scoreboard-score"] )
  damage_dealt  = int( player_data["scoreboard-pushes"] )
  damage_taken  = int( player_data["scoreboard-destroyed"] )
  frags_count   = int( player_data["scoreboard-kills"] )
  deaths_count  = int( player_data["scoreboard-deaths"] )
  capture_count = int( player_data["medal-captures"] )
  defends_count = int( player_data["medal-defends"] )
  assists_count = int( player_data["medal-assists"] )
  win           = 1 if "win" in player_data else 0

  if alive_time < MIN_ALIVE_TIME_TO_RATE:
    return None
  else:
    time_factor   = 1200./alive_time

  return {
    "ad": ( damage_dealt/100 + frags_count + capture_count ) * time_factor,
    "ctf": ( damage_dealt/damage_taken * ( score + damage_dealt/20 ) * time_factor ) / 2.35 + win*300,
    "tdm2v2": ( 0.5 * (frags_count - deaths_count) + 0.004 * (damage_dealt - damage_taken) + 0.003 * damage_dealt ) * time_factor,
    "tdm": ( 0.5 * (frags_count - deaths_count) + 0.004 * (damage_dealt - damage_taken) + 0.003 * damage_dealt ) * time_factor
  }[gametype]


def count_multiple_players_match_perf( gametype, all_players_data ):

  result = {}
  temp = []
  sum_perf = 0
  for player in all_players_data:
    team     = int(player["t"]) if "t" in player else 0
    steam_id = int(player["P"])
    perf     = count_player_match_perf( gametype, player ) if MIN_PLAYER_COUNT_TO_RATE[ gametype ] <= len(all_players_data) else None
    if perf != None:
      temp.append({
        "team":     team,
        "steam_id": steam_id,
        "perf":     perf
      })
      sum_perf += perf
    if team not in result:
      result[ team ] = {}
    result[ team ][ steam_id ] = { "perf": perf }

  return result


def post_process_avg_perf(cu, match_id, gametype_id, match_timestamp):
  """
  Updates players' ratings after playing match_id (using avg. perfomance)

  """
  def extra_factor( gametype, matches, wins, losses ):
    try:
      return {
        "tdm": (1 + (0.15 * (wins / matches - losses / matches)))
      }[gametype]
    except KeyError:
      return 1

  global LAST_GAME_TIMESTAMPS
  cu.execute("SELECT s.steam_id, team, match_perf, gr.mean FROM scoreboards s LEFT JOIN gametype_ratings gr ON gr.steam_id = s.steam_id AND gr.gametype_id = %s WHERE match_perf IS NOT NULL AND match_id = %s", [gametype_id, match_id])

  rows = cu.fetchall()
  for row in rows:
    steam_id   = row[0]
    team       = row[1]
    match_perf = row[2]
    old_rating = row[3]

    cu.execute("UPDATE scoreboards SET old_mean = %s, old_deviation = 0 WHERE match_id = %s AND steam_id = %s AND team = %s", [old_rating, match_id, steam_id, team])
    assert cu.rowcount == 1

    if old_rating == None:
      new_rating = match_perf
    else:
      query_string = '''
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
          s.steam_id = %s AND
          m.gametype_id = %s AND
          (m.post_processed = TRUE OR m.match_id = %s) AND
          s.match_perf IS NOT NULL
        ORDER BY m.timestamp DESC
        LIMIT %s
      ) t'''
      cu.execute(query_string, [steam_id, gametype_id, match_id, MOVING_AVG_COUNT])
      row = cu.fetchone()
      gametype = [k for k, v in GAMETYPE_IDS.items() if v == gametype_id][0]
      new_rating = row[3] * extra_factor( gametype, row[0], row[1], row[2] )

    cu.execute("UPDATE scoreboards SET new_mean = %s, new_deviation = 0 WHERE match_id = %s AND steam_id = %s AND team = %s", [new_rating, match_id, steam_id, team])
    assert cu.rowcount == 1

    cu.execute("UPDATE gametype_ratings SET mean = %s, deviation = 0, n = n + 1, last_played_timestamp = %s WHERE steam_id = %s AND gametype_id = %s", [new_rating, match_timestamp, steam_id, gametype_id])
    if cu.rowcount == 0:
      cu.execute("INSERT INTO gametype_ratings (steam_id, gametype_id, mean, deviation, last_played_timestamp, n) VALUES (%s, %s, %s, 0, %s, 1)", [steam_id, gametype_id, new_rating, match_timestamp])
    assert cu.rowcount == 1

  cu.execute("UPDATE matches SET post_processed = TRUE WHERE match_id = %s", [match_id])
  assert cu.rowcount == 1

  LAST_GAME_TIMESTAMPS[ gametype_id ] = match_timestamp


def post_process_trueskill(cu, match_id, gametype_id, match_timestamp):
  """
  Updates players' ratings after playing match_id (using trueskill)

  """
  global LAST_GAME_TIMESTAMPS
  cu.execute("SELECT team2_score > team1_score, team2_score < team1_score FROM matches WHERE match_id = %s", [ match_id ])
  row = cu.fetchone()
  team_ranks = [ row[0], row[1] ]

  cu.execute('''
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
      WHERE gametype_id = %s
    ) gr ON gr.steam_id = s.steam_id
    WHERE
      match_perf IS NOT NULL AND
      match_id = %s
    ''', [gametype_id, match_id])

  team_ratings_old = [ [], [] ]
  team_ratings_new = [ [], [] ]
  team_steam_ids   = [ [], [] ]
  rows = cu.fetchall()
  for row in rows:
    steam_id     = row[0]
    team         = row[1]
    # match_perf   = row[2]
    mean         = row[3]
    deviation    = row[4]

    try:
      team_ratings_old[ team - 1 ].append( trueskill.Rating( mean, deviation ) )
      team_steam_ids  [ team - 1 ].append( steam_id )
    except KeyError:
      continue

  if len( team_ratings_old[0] ) == 0 or len( team_ratings_old[1] ) == 0:
    cu.execute("UPDATE matches SET post_processed = TRUE WHERE match_id = %s", [match_id])
    assert cu.rowcount == 1

    LAST_GAME_TIMESTAMPS[ gametype_id ] = match_timestamp
    return

  team1_ratings, team2_ratings = trueskill.rate( team_ratings_old, ranks=team_ranks )
  team_ratings_new = [team1_ratings, team2_ratings]

  steam_ids   = team_steam_ids[0] + team_steam_ids[1]
  new_ratings = team1_ratings + team2_ratings
  old_ratings = team_ratings_old[0] + team_ratings_old[1]

  assert len(steam_ids) == len(new_ratings) == len(old_ratings)

  steam_ratings = {}
  for i in range( len(steam_ids) ):
    steam_id = steam_ids[i]

    if steam_id in steam_ratings: # player played for both teams. Ignoring...
      del steam_ratings[ steam_id ]

    steam_ratings[ steam_id ] = {
      "old": old_ratings[i],
      "new": new_ratings[i],
      "team": 1 if i < len(team1_ratings) else 2
    }

  for steam_id, ratings in steam_ratings.items():
    cu.execute('''
      UPDATE scoreboards
      SET
        old_mean = %s, old_deviation = %s,
        new_mean = %s, new_deviation = %s
      WHERE match_id = %s AND steam_id = %s AND team = %s
    ''', [ratings["old"].mu, ratings["old"].sigma, ratings["new"].mu, ratings["new"].sigma, match_id, steam_id, ratings["team"]])
    assert cu.rowcount == 1

    cu.execute("UPDATE gametype_ratings SET mean = %s, deviation = %s, n = n + 1, last_played_timestamp = %s WHERE steam_id = %s AND gametype_id = %s", [ratings['new'].mu, ratings['new'].sigma, match_timestamp, steam_id, gametype_id])
    if cu.rowcount == 0:
      cu.execute("INSERT INTO gametype_ratings (steam_id, gametype_id, mean, deviation, last_played_timestamp, n) VALUES (%s, %s, %s, %s, %s, 1)", [steam_id, gametype_id, ratings['new'].mu, ratings['new'].sigma, match_timestamp])
    assert cu.rowcount == 1

  cu.execute("UPDATE matches SET post_processed = TRUE WHERE match_id = %s", [match_id])
  assert cu.rowcount == 1

  LAST_GAME_TIMESTAMPS[ gametype_id ] = match_timestamp


def post_process(cu, match_id, gametype_id, match_timestamp):
  if USE_AVG_PERF[ gametype_id ]:
    return post_process_avg_perf(cu, match_id, gametype_id, match_timestamp)
  else:
    return post_process_trueskill(cu, match_id, gametype_id, match_timestamp)


def submit_match(data):
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
  try:
    match_id = None

    if type(data).__name__ == 'str':
      data = parse_stats_submission( data )

    if is_instagib(data):
      data["game_meta"]["G"] = "i" + data["game_meta"]["G"]

    if is_tdm2v2(data):
      data["game_meta"]["G"] = "tdm2v2"

    match_id = data["game_meta"]["I"]

    if data["game_meta"]["G"] not in GAMETYPE_IDS:
      return {
        "ok": False,
        "message": "gametype is not accepted: " + data["game_meta"]["G"],
        "match_id": match_id
      }

    db = db_connect()
    cu = db.cursor()

    team_scores = [None, None]
    team_index = -1
    for team_data in data["teams"]:
      team_index = int( team_data["Q"].replace("team#", "") ) - 1
      for key in ["scoreboard-rounds", "scoreboard-caps", "scoreboard-score"]:
        if key in team_data:
          team_scores[team_index] = int(team_data[key])
    team1_score, team2_score = team_scores

    match_timestamp = int( data["game_meta"]["1"] )
    cu.execute("INSERT INTO matches (match_id, gametype_id, factory_id, map_id, timestamp, duration, team1_score, team2_score, post_processed) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", [
      match_id,
      GAMETYPE_IDS[ data["game_meta"]["G"] ],
      get_factory_id( cu, data["game_meta"]["O"] ),
      get_map_id( cu, data["game_meta"]["M"] ),
      match_timestamp,
      int( data["game_meta"]["D"] ),
      team1_score,
      team2_score,
      cfg["run_post_process"]
    ])

    player_match_ratings = count_multiple_players_match_perf( data["game_meta"]["G"], data["players"] )
    for player in data["players"]:
      player["P"] = int(player["P"])
      if 'playermodel' not in player:
        player['playermodel'] = "sarge/default"
      team = int(player["t"]) if "t" in player else 0

      cu.execute( '''INSERT INTO players (
        steam_id,
        name,
        model,
        last_played_timestamp
      ) VALUES (%s, %s, %s, %s)
      ON CONFLICT (steam_id) DO UPDATE SET (name, model, last_played_timestamp) = (%s, %s, %s)
      WHERE players.last_played_timestamp < %s''', [
        player["P"],
        player["n"],
        player["playermodel"],
        match_timestamp,
        player["n"],
        player["playermodel"],
        match_timestamp,
        match_timestamp
      ])

      cu.execute('''INSERT INTO scoreboards (
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
      ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''', [
        match_id,
        player["P"],
        int( player["scoreboard-kills"] ),
        int( player["scoreboard-deaths"] ),
        int( player["scoreboard-pushes"] ),
        int( player["scoreboard-destroyed"] ),
        int( player["scoreboard-score"] ),
        player_match_ratings[ team ][ player["P"] ][ "perf" ],
        int( player["alivetime"] ),
        team
      ])

      for weapon, weapon_id in WEAPON_IDS.items():
        frags = int( player["acc-" + weapon + "-frags"] )
        shots = int( player["acc-" + weapon + "-cnt-fired"] )
        if frags + shots == 0:
          continue

        cu.execute("INSERT INTO scoreboards_weapons (match_id, steam_id, team, weapon_id, frags, hits, shots) VALUES (%s, %s, %s, %s, %s, %s, %s)", [
          match_id,
          player["P"],
          team,
          weapon_id,
          frags,
          int( player["acc-" + weapon + "-cnt-hit"] ),
          shots
        ])

      for medal, medal_id in MEDAL_IDS.items():
        medal_count = int( player["medal-" + medal] )
        if medal_count == 0:
          continue

        cu.execute("INSERT INTO scoreboards_medals (match_id, steam_id, team, medal_id, count) VALUES (%s, %s, %s, %s, %s)", [
          match_id,
          player["P"],
          team,
          medal_id,
          medal_count
        ])

    # post processing
    if cfg["run_post_process"] == True:
      post_process( cu, match_id, GAMETYPE_IDS[ data["game_meta"]["G"] ], match_timestamp )
      result = {
        "ok": True,
        "message": "done",
        "match_id": match_id
      }
    else:
      result = {
        "ok": True,
        "message": "skipped post processing",
        "match_id": match_id
      }

    db.commit()
  except Exception as e:
    db.rollback()
    log_exception(e)
    result = {
      "ok": False,
      "message": type(e).__name__ + ": " + str(e),
      "match_id": match_id
    }

  cu.close()
  db.close()

  return result


def reset_gametype_ratings( gametype ):
  """
  Resets ratings for gametype
  """
  if gametype not in GAMETYPE_IDS:
    print("gametype is not accepted: " + gametype)
    return False

  gametype_id = GAMETYPE_IDS[gametype]
  result = False
  try:
    db = db_connect()
    cu = db.cursor()
    cw = db.cursor()

    cw.execute('UPDATE matches SET post_processed = FALSE WHERE gametype_id = %s', [gametype_id])
    cw.execute('UPDATE gametype_ratings SET mean = %s, deviation = %s, n = 0 WHERE gametype_id = %s', [trueskill.MU, trueskill.SIGMA, gametype_id])
    scoreboard_query = '''
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
      ))
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
    '''

    cu.execute(scoreboard_query, [gametype_id])
    for row in cu:
      match_id = row[0]
      team1_score = row[1]
      team2_score = row[2]
      all_players_data = []
      for player in row[3]:
        if player['t'] == 1 and team1_score > team2_score:
          player['win'] = 1
        if player['t'] == 2 and team1_score < team2_score:
          player['win'] = 1
        all_players_data.append(player.copy())
      print(match_id)
      player_match_ratings = count_multiple_players_match_perf( gametype, all_players_data )

      for player in all_players_data:
        player["P"] = int(player["P"])
        team = int(player["t"]) if "t" in player else 0

        cw.execute(
          'UPDATE scoreboards SET match_perf = %s, new_mean = NULL, old_mean = NULL, new_deviation = NULL, old_deviation = NULL WHERE match_id = %s AND team = %s AND steam_id = %s', [
            player_match_ratings[ team ][ player["P"] ][ "perf" ],
            match_id, team, player["P"]
          ]
        )

    db.commit()
    result = True

  except Exception as e:
    db.rollback()
    log_exception(e)
  finally:
    cu.close()
    db.close()

  return result


db = db_connect()
cu = db.cursor()

if cfg["run_post_process"]:
  cu.execute("SELECT match_id, gametype_id, timestamp FROM matches WHERE post_processed = FALSE ORDER BY timestamp ASC")
  for row in cu.fetchall():
    print("running post process: " + str(row[0]) + "\t" + str(row[2]))
    post_process(cu, row[0], row[1], row[2])
    db.commit()

cu.close()
db.close()
