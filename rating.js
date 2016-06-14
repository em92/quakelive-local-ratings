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
        docs.forEach(function(doc, i) {
          result = {};
          var rank = (doc.n < 10) ? null : rank_cnt++;
          result[gametype] = {
            n: doc.n,
            rank: rank,
            rating: parseFloat(doc.rating.toFixed(2))
          };
          db.collection('players').update(
            {_id: doc._id},
            { $set: result }
          );
        });
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
