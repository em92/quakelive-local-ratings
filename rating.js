var MongoClient = require('mongodb').MongoClient;
var cfg = require("./cfg.js");
var Q = require('q');
var extend = require('util')._extend;

// Note:
// using promises/Q for the first time in my life

var MOVING_AVERAGE_COUNT = cfg.moving_average_count;
var MAX_RATING_HISTORY_COUNT = 50;
var GAMETYPES_AVAILABLE = ["ad", "ctf", "ictf", "tdm"];
var MATCH_RATING_CALC_METHODS = {
  'ad': { 'match_rating':
    { $multiply: [
      { $add: [
        { $divide: [ "$scoreboard.damage-dealt", 100 ] },
        "$scoreboard.kills",
        "$scoreboard.medals.captures"
      ]},
      { $divide: [ 1200, "$scoreboard.time" ] }
    ]}
  },
  'ctf': { 'match_rating':
    { $add: [
      { $multiply: [
        1/2.35,
        { $divide: [ "$scoreboard.damage-dealt", "$scoreboard.damage-taken" ] },
        { $add: [ "$scoreboard.score", { $divide: [ "$scoreboard.damage-dealt", 20 ] } ] },
        { $divide: [ 1200, "$scoreboard.time" ] }
      ]},
      { $multiply: [
        1/2.35,
        300,
        { $cond: ["$scoreboard.win", 1, 0] }
      ]}
    ]}
  },
  'ictf': { 'match_rating':
    { $add: [
      { $multiply: [
        1/2.35,
        { $divide: [ "$scoreboard.damage-dealt", "$scoreboard.damage-taken" ] },
        { $add: [ "$scoreboard.score", { $divide: [ "$scoreboard.damage-dealt", 20 ] } ] },
        { $divide: [ 1200, "$scoreboard.time" ] }
      ]},
      { $multiply: [
        1/2.35,
        300,
        { $cond: ["$scoreboard.win", 1, 0] }
      ]}
    ]}
  },
  'tdm': { 'match_rating': 
    { $add: [
      { $multiply: [ 0.5, { $subtract: ["$scoreboard.kills", "$scoreboard.deaths"] } ] },
      { $multiply: [ 0.004, { $subtract: [ "$scoreboard.damage-dealt", "$scoreboard.damage-taken" ] } ] },
      { $multiply: [ 0.003, "$scoreboard.damage-dealt" ] }
    ]}
  }
};

var RATING_FACTORS = {
  'ad': 1,
  'ctf': 1,
  'ictf': 1,
  'tdm': {
    $add: [
      1,
      { $multiply: [ 0.15, { $subtract: [
        { $divide: ["$w", "$n"] }, { $divide: ["$l", "$n"] }
      ] } ] },
    ]
  }
};


var connect = function(callback, fuck) {
  MongoClient.connect(cfg['db_url'], function(err, db) {
    if (err)
      fuck(err);
    else
      callback(db);
  });
};


var in_array = function(what, array) {
  return array.some(function(param) {return param==what});
};


var get_aggregate_options = function(gametype, after_unwind, after_project, is_post_processed) {
  if (typeof(is_post_processed) == 'undefined') is_post_processed = true;
  return [].concat([
    { $match: { "is_post_processed": is_post_processed } },
    { $match: { "gametype": gametype } },
    { $lookup: {
      from: "scoreboards",
      localField: "_id",
      foreignField: "_id.match_id",
      as: "scoreboard"
    } },
    { $unwind: "$scoreboard" },
    { $match: { "scoreboard.time": { $gt: 300 } } },
    { $match: { "scoreboard.damage-taken": { $gt: 100 } } }
  ], after_unwind, [
    { $project: extend({"timestamp": 1, "scoreboard": 1}, MATCH_RATING_CALC_METHODS[gametype]) },
    { $sort: { "timestamp": 1 } },
    { $group: {
      _id: "$scoreboard._id.steam_id",
      n: { $sum: 1 },
      w: { $sum: { $cond: ["$scoreboard.win", 1, 0] } },
      l: { $sum: { $cond: ["$scoreboard.win", 0, 1] } },
      last_match_id: { $last: "$_id" },
      last_match_timestamp: { $last: "$timestamp" },
      match_ratings: { $push: "$match_rating" },
    }},
    { $project: {
      _id: 1,
      n: 1,
      last_match_id: 1,
      last_match_timestamp: 1,
      rating: { $multiply: [ { $avg: { $slice: [
        "$match_ratings",
        { $max: [ { $subtract: ["$n", MOVING_AVERAGE_COUNT] }, 0] }, // max(n-20,0)
        { $min: [ "$n", MOVING_AVERAGE_COUNT ] } // min(n,20)
      ] } }, RATING_FACTORS[gametype] ] }
    }}
  ], after_project);
};


var parse_stats_submission = function(body) {
  var len = function(obj) {
    return Object.keys(obj).length;
  };

  // storage vars for the request body
  var game_meta = {};
  var events = {};
  var players = [];
  var teams = [];

  // we're not in either stanza to start
  var in_P = false;
  var in_Q = false;
  var lines = body.split("\n");
  for(var k=0; k<lines.length; k++) {
    var line = lines[k];
    var key = line.substr(0, line.indexOf(' '));
    var value = line.substr(line.indexOf(' ')+1);

    if (in_array(key, ['P', 'Q', 'n', 'e', 't', 'i']) == false) {
      game_meta[key] = value;
    }
    
    if (in_array(key, ['Q', 'P'])) {
      //log.debug('Found a {0}'.format(key))
      //log.debug('in_Q: {0}'.format(in_Q))
      //log.debug('in_P: {0}'.format(in_P))
      //log.debug('events: {0}'.format(events))

      // check where we were before and append events accordingly
      if ( in_Q && (len(events) > 0) ) {
        // log.debug('creating a team (Q) entry')
        teams.push(events);
        events = {};
      } else if (in_P && (len(events) > 0) ) {
        // log.debug('creating a player (P) entry')
        players.push(events);
        events = {};
      }

      if (key == 'P') {
        //log.debug('key == P')
        in_P = true;
        in_Q = false;
      } else if (key == 'Q') {
        //log.debug('key == Q')
        in_P = false;
        in_Q = true;
      }

      events[key] = value;
    }
    
    
    if (key == 'e') {
      var subkey = value.split(' ')[0];
      var subvalue = value.split(' ')[1];
      events[subkey] = subvalue;
    }
    if (key == 'n') {
      events[key] = value;
    }
    if (key == 't') {
      events[key] = value;
    }
  }

  // add the last entity we were working on
  if (in_P && (len(events) > 0) ) {
    players.push(events);
  } else if (in_Q && (len(events) > 0) ) {
    teams.push(events);
  }
  
  return {game_meta: game_meta, players: players, teams: teams};
};


var is_instagib = function(data) {
  return data.players.every( player => {
    return ['mg', 'sg', 'gl', 'rl', 'lg', 'pg', 'hmg', 'bfg', 'cg', 'ng', 'pm', 'gh'].every( weapon => {
      if (typeof( player['acc-' + weapon + '-cnt-fired'] ) == 'undefined') {
        return true;
      } else if ( player['acc-' + weapon + '-cnt-fired'] == '0' ) {
        return true;
      } else {
        return false;
      }
    });
  });
};

var updateRatings = function(db, docs, gametype, playerRanks) {
  return Q.all(docs.map(function(doc) {
    var result = {};
    result[gametype + ".n"] = doc.n;
    result[gametype + ".rating"] = parseFloat(doc.rating.toFixed(2));
    return Q(db.collection('players').update(
      {_id: doc._id },
      { $set: result }
    ))
    .then( () => {
      if (playerRanks) {
        return db.collection('scoreboards').update(
          { "_id.match_id": doc.last_match_id, "_id.steam_id": doc._id },
          { $set: { history_rating: parseFloat(doc.rating.toFixed(2)), history_rank: playerRanks[doc._id]} }
        );
      } else {
        return true;
      }
    })
    .catch( error => {
      console.error(error);
console.error(error.trace);
    });
  }));
};


var countPlayerRanks = function(db, gametype, steamIds) {
  var result = {};
  var tasks = new Set();
  steamIds.forEach( steamId => {
    tasks.add( steamId );
    result[ steamId ] = 0;
  });

  var matching = {};
  matching[gametype + ".n"] = { $gte: 10 };

  var sorting = {};
  sorting[gametype + ".rating"] = -1;

  return new Promise( (resolve, reject) => {
    var cursor = db.collection('players').aggregate([
      {$match: matching}, {$sort: sorting}
    ]);
    var rank = 1;
    var handler = function(err, doc) {
      if (err) {
        console.error(err);
        cursor.close();
        reject(err);
        return;
      }

      if (doc == null) {
        cursor.close();
        resolve( result );
        return;
      }

      if (tasks.has(doc._id)) {
        tasks.delete(doc._id);
        result[ doc._id ] = rank;
      };

      if (tasks.size == 0) {
        cursor.close();
        resolve( result );
        return;
      }

      rank++;
      cursor.nextObject(handler);
    };

    cursor.nextObject(handler);
  });
};


var postProcess = function(db, matchId, gametype, steamIds) {
  var playerRanks = {};

  return Q(countPlayerRanks(db, gametype, steamIds))
  .then( result => {

    playerRanks = result;

    return db.collection('matches').aggregate( get_aggregate_options(
      gametype, [ { $match: { "_id": matchId } } ], [ ], false
    )).toArray();

  })
  .then(function(docs) {

    return updateRatings(db, docs, gametype, playerRanks)
    .then( () => {

      return db.collection('matches').update(
        {_id: matchId},
        {$set: { is_post_processed: true } }
      );
    })
    .catch( error => {
      console.error(e);
    });
  });
};


var submitMatch = function(data, run_post_process, done) {

  if (typeof(data) == 'string') {
    data = parse_stats_submission(data);
  }

  if (is_instagib(data)) {
    data.game_meta["G"] = "i" + data.game_meta["G"];
  }

  if (in_array(data.game_meta["G"], GAMETYPES_AVAILABLE) == false ) {
    done({ok: false, message: "gametype is not accepted: " + data.game_meta["G"], match_id: data.game_meta["I"]});
    return;
  }
  
  connect(function(db) {

    var scoreboards = data.players.map(function(item) {
      var medalList = [
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
      ];
      var medals = {};
      medalList.forEach( medal_name => {
        medals[medal_name] = parseInt(item["medal-" + medal_name]);
      });
      var weaponList = ['gt', 'mg', 'sg', 'gl', 'rl', 'lg', 'rg', 'pg', 'hmg'];
      var weapons = {};
      weaponList.forEach( w => {
        weapons[w] = {
          hits: parseInt(item["acc-" + w + "-cnt-hit"]),
          shots: parseInt(item["acc-" + w + "-cnt-fired"]),
          frags: parseInt(item["acc-" + w + "-frags"])
        };
      });
      var team = item["t"] ? parseInt(item["t"]) : 0;
      return {
        "_id": {"steam_id": item["P"], "match_id": data.game_meta["I"], "team": team},
        "score": parseInt(item["scoreboard-score"]),
        "kills": parseInt(item["scoreboard-kills"]),
        "deaths": parseInt(item["scoreboard-deaths"]),
        'damage-dealt': parseInt(item["scoreboard-pushes"]),
        'damage-taken': parseInt(item["scoreboard-destroyed"]),
        "time": parseInt(item["alivetime"]),
        "medals": medals,
        "weapons": weapons,
        "win": item["win"] ? true : false
      };
    });

    Q(db.collection('matches').insertOne({
      _id: data.game_meta["I"],
      map: data.game_meta["M"],
      gametype: data.game_meta["G"],
      factory: data.game_meta["O"],
      timestamp: parseInt(data.game_meta["1"]),
      is_post_processed: false,
    }))
    .then( () => {
      return db.collection('scoreboards').insertMany(scoreboards);
    })
    .then(Q.all(data.players.map( player => {
      return db.collection('players').update(
        {_id: player["P"]},
        { $set: { name: player["n"], model: player["playermodel"] } },
        {upsert: true}
      );
    })))
    .then(function() {

      if (run_post_process == false)
        throw new Error("skipped post processing");

      return postProcess( db, data.game_meta["I"], data.game_meta["G"], data.players.map( player => { return player["P"] }) );
    })

    .then(function() {

       done({ok: true, match_id: data.game_meta["I"]});

    })
    .catch(function(err) {

      if ( (err.name == "MongoError") && (err.code == 11000) ) {
        done({ok: false, message: err.message, match_id: data.game_meta["I"], match_already_exists: true});
      } else {
        done({ok: false, message: err.message, match_id: data.game_meta["I"]});
      }

    })
    .finally(function() {

      db.close();

    });

  }, function(err) {

      done({ok: false, message: err.toString(), match_id: data.game_meta["I"]});

  });

};

var getList = function(gametype, page, done) {

  connect(function(db) {

    var matching = {}; matching[gametype + ".n"] = { $gte: 10 };
    var sorting  = {};  sorting[gametype + ".rating"] = -1;

    var project  = {
      _id: "$_id",
      name: "$name",
    };
    project.n      = "$" + gametype + ".n";
    project.rating = "$" + gametype + ".rating";

    var docs = [];

    Q(db.collection('players').aggregate([
      { $match: matching },
      { $sort: sorting },
      { $skip: page * cfg['player_count_per_page'] },
      { $limit: cfg['player_count_per_page'] },
      { $project: project }
    ]).toArray())
    .then(function(result) {

      docs = result.map(function(item, i) {
        item.rank = page * cfg['player_count_per_page'] + 1 + i;
        return item;
      });
      return db.collection('players').find(matching).count();

    })
    .then(function(count) {

       done({ok: true, response: docs, page_count: Math.ceil(count / cfg['player_count_per_page'])});

    })
    .catch(function(err) {

      done({ok: false, message: err.toString()});

    })
    .finally(function() {

      db.close();

    });

  }, function(err) {

    done({ok: false, message: err.toString()});

  });

};


var getForBalancePlugin = function(steamIds, done) {

  var project = {};
  project._id = 0;
  project.steamid = "$_id";
  GAMETYPES_AVAILABLE.forEach(function(gametype) {
    project[gametype] = {
      games: "$" + gametype + ".n",
      elo: "$" + gametype + ".rating",
    };
  });

  connect(function(db) {

    Q.all(db.collection('players').aggregate([
        { $match: {"_id": { $in: steamIds } } },
        { $project: project }
    ]).toArray())
    .then(function(docs) {

      done({ok: true, players: docs, deactivated: []});

    }).catch(function(err) {

      done({ok: false, message: err.toString()});

    }).finally(function() {

      db.close();

    });

  }, function(err) {

    done({ok: false, message: err.toString()});

  });
};


var getPlayerInfo = function(steamId, done) {

  connect(function(db) {

    Q(db.collection('players').findOne({"_id": steamId}))
    .then(function(doc) {

      done({ok: true, player: doc});

    }).catch(function(err) {

      done({ok: false, message: err.toString()});

    }).finally(function() {

      db.close();

    });

  }, function(err) {

    done({ok: false, message: err.toString()});

  });

};


var update = function(done) {

  if (typeof(done) == 'undefined') {
    done = function() {};
  }

  connect(function(db) {

    Q.all(GAMETYPES_AVAILABLE.map(function(gametype) {

      return db.collection('matches').aggregate( get_aggregate_options(
        gametype, [], [ { $sort: { "rating": -1 } } ]
      )).toArray();

    }))
    .then(function(docs_docs) {

      return Q.all(GAMETYPES_AVAILABLE.map(function(gametype, i) {
        var docs = docs_docs[i];
        return updateRatings(db, docs, gametype);
      }));

    })
    .then(function(docs_docs) {

      return Q.all(GAMETYPES_AVAILABLE.map(function(gametype, i) {
        var cursor = db.collection('matches').aggregate([
          { $match: { "is_post_processed": false } },
          { $match: { "gametype": gametype } },
          { $lookup: {
            from: "scoreboards",
            localField: "_id",
            foreignField: "_id.match_id",
            as: "scoreboard"
          } },
          { $unwind: "$scoreboard" },
          { $match: { "scoreboard.time": { $gt: 300 } } },
          { $match: { "scoreboard.damage-taken": { $gt: 100 } } },
          { $group: { "_id": "$_id", "timestamp": { $avg: "$timestamp" }, "steam_ids": { $push: "$scoreboard._id.steam_id" } } },
          { $sort: { "timestamp": 1 } }
        ]);
        return new Promise( (resolve, reject) => {
          var handler = function(err, match) {
            if (err) {
              cursor.close();
              reject(err);
              return;
            }

            if (match == null) {
              cursor.close();
              return resolve();
            };
            var datestring = (new Date(match.timestamp*1000)).toISOString().replace("T", " ").replace(".000Z", "");
            console.log( match._id + " " + datestring + " " + gametype);
            postProcess( db, match._id, gametype, match.steam_ids )
            .then( () => {
              cursor.nextObject(handler);
            });
          };
          cursor.nextObject(handler);
        });
      }));
    })
    .then(function() {

      done({ok: true});

    }).catch(function(err) {

      done({ok: false, message: err.toString()});

    }).finally(function() {

      db.close();

    });

  }, function(err) {

    done({ok: false, message: err.toString()});

  });
};

module.exports.update = update;
module.exports.getList = getList;
module.exports.getPlayerInfo = getPlayerInfo;
module.exports.getForBalancePlugin = getForBalancePlugin;
module.exports.submitMatch = submitMatch;
