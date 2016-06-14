var express = require('express');
var rating = require('./rating.js');

var LISTEN_PORT = requie("./cfg.json").httpd_port;
var app = express();


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


app.post("/stats/submit", function(req, res) {
  // ToDo: добавить проверку заголовка (посмотри у фидера)
  // ToDo: добавить результаты матча
  // ToDo: выдернуть имена и засунуть в коллекцию players
  // ToDo: пересчитать 
  // ToDo: в это время считают рейтинг, то добавить в очередь для считывания
  res.setHeader("Content-Type", "application/json");
  res.send({ok: false});
});


app.use(express.static("public"));


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
