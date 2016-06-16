var MongoClient = require('mongodb').MongoClient;
var ObjectID = require('mongodb').ObjectID;
var cfg = require("./cfg.json");
var Q = require('q');
var extend = require('util')._extend;

// Note:
// using promises/Q for the first time in my life

var GAMETYPES_AVAILABLE = ["ctf", "tdm"];
var MATCH_RATING_CALC_METHODS = {
  'ctf': { 'match_rating':
    { $add: [
      { $multiply: [
        1/2.35,
        { $divide: [ "$scoreboard.damage-dealt", "$scoreboard.damage-taken" ] },
        { $add: [ "$scoreboard.score", { $divide: [ "$scoreboard.damage-dealt", 1000 ] } ] },
        { $divide: [ 1200, "$scoreboard.time" ] }
      ]},
      { $multiply: [
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
  'ctf': 1,
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
  MongoClient.connect(cfg['db-url'], function(err, db) {
    if (err)
      fuck(err);
    else
      callback(db);
  });
};


var get_aggregate_options = function(gametype, after_unwind, after_project) {
  return [].concat([
    { $match: { "gametype": gametype } },
    { $unwind: "$scoreboard" },
    { $match: { "scoreboard.time": { $gt: 300 } } }
  ], after_unwind, [
    { $project: extend({"scoreboard.steam-id": 1, "scoreboard.win": 1}, MATCH_RATING_CALC_METHODS[gametype]) },
    { $group: {
      _id: "$scoreboard.steam-id", 
      n: { $sum: 1 },
      w: { $sum: { $cond: ["$scoreboard.win", 1, 0] } },
      l: { $sum: { $cond: ["$scoreboard.win", 0, 1] } },
      "rating": {$avg: "$match_rating"}
    }},
    { $project: {
      _id: 1,
      n: 1,
      rating: { $multiply: ["$rating", RATING_FACTORS[gametype]] }
    }}
  ], after_project);
};


var parse_stats_submission = function(body) {
  var len = function(obj) {
    return Object.keys(obj).length;
  };
  
  var in_array = function(what, array) {
    return array.some(function(param) {return param==what});
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


var updateRanks = function(db, docs, gametype) {
  return Q.all(docs.map(function(doc) {
    result = {};
    var rank = (doc.n < 10) ? null : rank_cnt++;
    result[gametype] = {
      n: doc.n,
      rank: rank,
      rating: parseFloat(doc.rating.toFixed(2))
    };
    return db.collection('players').update(
      {_id: doc._id},
      { $set: result }
    );
  }))
};


var submitMatch = function(data, done) {

  data = parse_stats_submission(data);

  connect(function(db) {

    var scoreboard = data.players.map(function(item) {
      return {
        "steam-id": item["P"],
        "score": parseInt(item["scoreboard-score"]),
        "kills": parseInt(item["scoreboard-kills"]),
        "deaths": parseInt(item["scoreboard-deaths"]),
        'damage-dealt': parseInt(item["scoreboard-pushes"]),
        'damage-taken': parseInt(item["scoreboard-destroyed"]),
        "time": parseInt(item["alivetime"]),
        "win": item["win"] ? true : false
      };
    });

    Q(db.collection('matches').insertOne({
      _id: data["I"],
      map: data["M"],
      gametype: data["G"],
      factory: data["O"],
      scoreboard: scoreboard
    }))
    .then(function() {

      return Q.all(data.players.map(function(player) {
        return db.collection('players').update(
          {_id: player["P"]},
          { $set: {"name": player["n"]} }
        );
      }));

    })
    .then(function() {

      var steamIds = data.players.map(function(item) {
        return item["P"];
      });
      
      return db.collection('matches').aggregate( get_aggregate_options(
        gametype, [ { $match: { "scoreboard.steam-id": { $in: steamIds } } } ], [ { $sort: { "rating": -1 } } ]
      )).toArray()

    })
    .then(function(docs) {

      return updateRanks(db, docs, data["G"]);

    })
    .then(function() {

       done({ok: true});

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

var getList = function(gametype, page, done) {

  connect(function(db) {

    var matching = {}; matching[gametype + ".rank"] = { $ne: null };
    var sorting  = {};  sorting[gametype + ".rank"] = 1;

    var project  = {
      _id: "$_id",
      name: "$name",
    };
    project.n      = "$" + gametype + ".n";
    project.rank   = "$" + gametype + ".rank";
    project.rating = "$" + gametype + ".rating";

    var docs = [];

    Q(db.collection('players').aggregate([
      { $match: matching },
      { $sort: sorting },
      { $skip: page * cfg['player-count-per-page'] },
      { $limit: cfg['player-count-per-page'] },
      { $project: project }
    ]).toArray())
    .then(function(result) {

      docs = result;
      return db.collection('players').find(matching).count();

    })
    .then(function(count) {

       done({ok: true, response: docs, page_count: parseInt(count / cfg['player-count-per-page'])});

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
      elo: "$" + gametype + ".rating"
    }
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

      GAMETYPES_AVAILABLE.forEach(function(gametype, i) {
        var docs = docs_docs[i];
        var rank_cnt = 1;
        updateRanks(db, docs, gametype);
      });

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
module.exports.getForBalancePlugin = getForBalancePlugin;
module.exports.submitMatch = submitMatch;
