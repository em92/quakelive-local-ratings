var express = require('express');
var bodyParser = require('body-parser');
var rating = require('./rating.js');

var LISTEN_PORT = require("./cfg.json").httpd_port;
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


app.get(["/rating/:gametype", "/rating/:gametype/:page"], function(req, res) {

  var page = get_int_from_string(req.params.page, 0);

  rating.getList(req.params.gametype, page, function(result) {
    res.setHeader("Content-Type", "application/json");
    res.send(result);
  });
});


app.post('/stats/submit', function (req, res) {
  rating.submitMatch(req.body, function(result) {
    res.setHeader("Content-Type", "application/json");
    res.send(result);
  });
  // ToDo: добавить проверку заголовка (посмотри у фидера)
  // ToDo: в это время считают рейтинг, то добавить в очередь для считывания
});


app.listen(LISTEN_PORT, function () {
  console.log("Listening on port " + LISTEN_PORT.toString());
  console.log("Updating ratings...");
  rating.update(function(result) {
    if (result.ok == true) {
      console.log("Updated successfully");
    } else {
      console.error(result.message);
    }
  });
});
