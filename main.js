var cfg = require("./cfg.js");
var express = require('express');
var bodyParser = require('body-parser');
var rating = require('./rating.js');

var LISTEN_PORT = cfg.httpd_port;
var RUN_POST_PROCESS = cfg.run_post_process;
var app = express();

app.use(bodyParser.text());
app.use(express.static("public"));


var get_int_from_string = function(s, default_value) {

  if (typeof(s) == 'undefined')
    return default_value;

  var result = parseInt(s);
  if (typeof(result) != "number")
    return default_value;

  return result;
};


app.get(["/elo/:ids", "/elo_b/:ids"], function(req, res) {

  var ids = req.params.ids.split("+");

  rating.getForBalancePlugin(ids, function(result) {
    res.setHeader("Content-Type", "application/json");
    res.send(result);
  });
});


app.get("/player/:id", function(req, res) {

  rating.getPlayerInfo(req.params.id, function(result) {
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


app.post('/stats/submit', function (req, res) {
  // https://github.com/PredatH0r/XonStat/blob/cfeae1b0c35c48a9f14afa98717c39aa100cde59/feeder/feeder.node.js#L989
  if (req.header("X-D0-Blind-Id-Detached-Signature") != "dummy") {
    console.error(req.connection.remoteAddress + ": signature header not found");
    res.status(403).json( {ok: false, message: "signature header not found"} );
    return;
  }
  
  if ( (req.connection.remoteAddress != '::ffff:127.0.0.1') && (req.connection.remoteAddress != '::1') ) {
    console.error(req.connection.remoteAddress + ": non-loopbacks requests are denied");
    res.status(403).json( {ok: false, message: "non-loopbacks requests are denied"} );
    return;
  }
  
  rating.submitMatch(req.body, RUN_POST_PROCESS, function(result) {
    if (result.ok == false) {
      console.error(result.match_id + ": " + result.message);
    } else {
      console.log(result.match_id + ": ok");
    }
    
    if (RUN_POST_PROCESS) {
      res.status(200).json( result );
    } else {
      res.status(403).json( result );
    }
  });
});


app.listen(LISTEN_PORT, function () {
  console.log("Listening on port " + LISTEN_PORT.toString());
  
  if (RUN_POST_PROCESS == false) return;
  
  console.log("Updating ratings...");
  rating.update(function(result) {
    if (result.ok == true) {
      console.log("Updated successfully");
    } else {
      console.error(result.message);
    }
  });
});
