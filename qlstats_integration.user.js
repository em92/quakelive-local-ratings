// ==UserScript==
// @name        QLStats.net + QLLR
// @namespace   http://eugene24.ru/
// @include     http://qlstats.net/game/*
// @version     1
// @grant       none
// ==/UserScript==

var match_id = $("#xonborder .note").html().trim();

$.get("http://vds2.eugene24.ru:7083/scoreboard/" + match_id, function( data ) {
  if (data.ok == false) return;
  
  var steam_ids = data.steam_ids;
  var team_ids = {"red": "1", "blue": "2"};
  
  $(".game tr").each( function() {
    if (this.className == "") {
      $(this).find("th").last().html("Rating Change");
      $(this).find("th").last().prev().html("Old Rating");
      return;
    }
    
    var team_id = team_ids[ this.className ];
    var player_id = $(this).find("a").attr('href').replace("/player/", "");
    var steam_id = steam_ids[ player_id ];
    var old_rating = data.team_stats.rating_history[ team_id ][ steam_id ].old_rating;
    var new_rating = data.team_stats.rating_history[ team_id ][ steam_id ].new_rating;
    var perf = data.team_stats.rating_history[ team_id ][ steam_id ].match_rating;
    
    var rating_change_block = $(this).find("td").last();
    if (old_rating != null && new_rating != null) {
      rating_change_block.html( (new_rating - old_rating).toFixed(2) );
    } else {
      rating_change_block.html( '<td><i class="glyphicon glyphicon-minus"></i></td>' );
    }
    
    var old_rating_block = $(this).find("td").last().prev();
    if (old_rating != null) {
      old_rating_block.html( old_rating.toFixed(2) );
    } else {
      old_rating_block.html( '<td><i class="glyphicon glyphicon-minus"></i></td>' );
    }
    
    var perf_block = $(this).find("td").last().prev().prev();
    if (perf != null) {
      perf_block.html( perf.toFixed(2) );
    } else {
      perf_block.html( '<td><i class="glyphicon glyphicon-minus"></i></td>' );
    }
  });
});