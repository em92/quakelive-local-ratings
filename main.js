var express = require('express');
var calcRating = require('./calc-rating.js');

var app = express();


app.get(["/elo/:ids", "/elo_b/:ids"], function(req, res) {
  ids = req.params.ids.split("+");
  calcRating(ids, function(result) {
    res.setHeader("Content-Type", "application/json");
    res.send(result);
  });
});


app.listen(6480, function () {
  console.log("6480");
});
