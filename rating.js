var MongoClient = require('mongodb').MongoClient;
var ObjectID = require('mongodb').ObjectID;
var cfg = require("./cfg.json");
var Q = require('q');
var extend = require('util')._extend;

// ToDo: 
// - перенести все ответы в формат { ok: true/false }
// - создать коллекцию, для хранения имен, steamid и для каждого режима n, rating, rank
// - с этой-же коллекции читать /elo и elo_b
// - проверить че там с цтф

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
	/* tdm ratio = 
	 * (avgNetFrags * 0.5 + avgNetDamage / 100 * 0.4 + avgDamageDone / 100 * 0.3) * 
	 * (1 + (0.15 * (wins / matches - losses / matches)))
	*/
	
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
		{ $project: extend({"scoreboard.steam-id": 1, "scoreboard.win": 1}, MATCH_RATING_CALC_METHODS[gametype]) },
		{ $match: { "n": { $gte: 10 } } }/*,
		{ $project: {
			rating: RATING_CALC_METHODS[gametype],
			n: "$n"
		}}*/
	]);//, after_project);
};


var getRatingList = function(gametype, page, done) {
	
	connect(function(db) {
		
		db.collection('matches').aggregate( get_aggregate_options(
			gametype, 
			[], [
				{ $sort: { "rating": -1 } },
				{ $skip: page * cfg['player-count-per-page'] },
				{ $limit: cfg['player-count-per-page'] }
			]
		)).toArray(function(err, docs) {
			
			if (err) {
				done(err);
				return;
				
			} else {
				
				result = docs.map(function(doc, i) {
					return {
						rank: i+1+page*cfg['player-count-per-page'],
						// ToDo: name
						steamid: doc._id,
						n: doc.n,
						rating: doc.rating
					};
				});
				
				done(result);
			
			}
		});
		
	}, function(err) {
		done(err);
	});
	
};


var getRatingsForSteamIds = function(steamIds, done) {

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
			db.collection('matches').aggregate( get_aggregate_options(
				gametype, 
				[ { $match: { "scoreboard.steam-id": { $in: steamIds } } } ],
				[]
			)).toArray(function(err, docs) {
				
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

module.exports.getForSteamIds = getRatingsForSteamIds;
module.exports.getList = getRatingList;
