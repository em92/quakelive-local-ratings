var MongoClient = require('mongodb').MongoClient;
var ObjectID = require('mongodb').ObjectID;
var url = require("./cfg.json")['db-url'];
var Q = require('q');

var connect = function(callback, fuck) {
	MongoClient.connect(url, function(err, db) {
		if (err)
			fuck(err);
    else
		  callback(db);
	});
};

var GAMETYPES_AVAILABLE = ["ad"];
var RATING_CALC_METHODS = {
  'ad': { $multiply: [
					1/2.35,
					{ $divide: [ { $avg: "$dg" }, { $avg: "$dt" } ] } , 
					{ $sum: [ { $avg: "$s" }, { $divide: [ { $avg: "$dg" }, 1000 ] } ] },
					{ $divide: [ 1200, { $avg: "$t" } ] }
				]}
};


var main = function(steamIds, done) {

  // default result
  result = { "players": steamIds.map(function(steamId) {
    temp = { "steamid": steamId };
    GAMETYPES_AVAILABLE.forEach(function(gametype) {
      temp[gametype] = { "games": 0, "elo": 0 };
    });
    return temp;
  })};
  
  connect(function(db) {
    
    GAMETYPES_AVAILABLE.forEach(function(gametype) {
      db.collection('matches').aggregate([
        { $match: { "gametype": gametype } },
        { $unwind: "$scoreboard" },
        { $match: { "scoreboard.steam-id": { $in: steamIds } } },
        { $group: {
          _id: "$scoreboard.steam-id", 
          n: {$sum: 1},
          dg: {$push: "$scoreboard.damage-dealt"},
          dt: {$push: "$scoreboard.damage-taken"},
          s: {$push: "$scoreboard.score"},
          t: {$push: "$scoreboard.time"},
          k: {$push: "$scoreboard.kills"},
          d: {$push: "$scoreboard.deaths"}
        }},
        { $match: { "n": { $gte: 10 } } },
        { $project: {
          rating: RATING_CALC_METHODS[gametype],
          n: "$n"
        }}
      ]).toArray(function(err, docs) {
        
        if (err) {
          done(err);
          return;
          
        } else {
          
          Q.all(docs.map(function(doc) {
            
            result["players"].forEach(function(player, i) {
              if (player["steamid"] == doc._id) {
                result["players"][i][gametype] = {
                  games: doc.n,
                  elo: parseFloat(doc.rating.toFixed(2))
                }
              }
            });
            
          })).then(function() {
            
            done(result);
            
          });
          
        }
      });
    });
    
  }, function(err) {
    done(err);
  });
};

module.exports = main;
