var express = require('express');
var rating = require('./rating.js');

var LISTEN_PORT = 6480;

var app = express();


var get_int_from_string = function(s, default_value) {
	
	if (typeof(s) == 'undefined')
		return default_value;
	
	var result = parseInt(s);
	if (isNan(result))
		return default_value;
	
	return result;
};


app.get(["/elo/:ids", "/elo_b/:ids"], function(req, res) {
	
	var ids = req.params.ids.split("+");
	
	rating.getForSteamIds(ids, function(result) {
		res.setHeader("Content-Type", "application/json");
		res.send(result);
	});
});


app.get(["/rating/:gametype", "/rating/:gametype/:page"], function(req, res) {
	
	var page = get_int_from_string(req.params.page, 0);
	
	rating.getList(req.params.gametype, page, function(result) {
		res.setHeader("Content-Type", "application/json");
		res.send(result);
	});

});


app.use(express.static("public"));

app.listen(LISTEN_PORT, function () {
	console.log("Listening on port " + LISTEN_PORT.toString());
});

rating.getList("tdm", 0, console.log);
