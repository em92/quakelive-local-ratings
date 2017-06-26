var GAMETYPES_AVAILABLE = ['ad', 'ctf', 'tdm', 'tdm2v2'];

function drawRatings(self) {
  var gametype = this.params['gametype'] ? this.params['gametype'].toLowerCase() : "undefined";
  var page     = this.params['page']     ? parseInt(this.params['page'])         : 0;

  if ( $.inArray( gametype, GAMETYPES_AVAILABLE ) == -1 ) {
    this.$element().html( "invalid gametype: " + gametype );
    return;
  }

  this.log( gametype );
  this.log( page );
  $.get('/rating/' + gametype + '/' + page)
  .done( function( data ) {
    self.render('templates/ratinglist.html', {list: data.response, page_count: data.page_count, current_page: page, gametype: gametype}).replace( self.$element() );
  });
};

function drawPlayerInfo(self) {
  var steam_id = this.params['steam_id'];
  var gametype = this.params['gametype'];

  if ( $.inArray( gametype, GAMETYPES_AVAILABLE ) == -1 ) {
    this.$element().html( "invalid gametype: " + gametype );
    return;
  }

  var chart_block = this.$element().get( 0 );
  $.get('/player/' + steam_id)
  .done( function( player_info ) {
    var history = player_info.player[ gametype ].history;
    var chart = new google.visualization.ColumnChart( chart_block );
    var options = {
      bar: {groupWidth: "50%"},
      height: 400,
      explorer: { keepInBounds: true }
    };
    var data = new google.visualization.DataTable();
    data.addColumn('string', 'Date');
    data.addColumn('number', 'Rating');
    data.addRows(history.map( function (item, i) {
      return [new Date(item.timestamp*1000).toLocaleFormat('%d-%b-%Y %H:%M:%S'), item.rating];
    }));
    chart.draw(data, options);
  });
};

function drawLastMatches(self) {
  var gametype = this.params['gametype'];

  if ( gametype && $.inArray( gametype, GAMETYPES_AVAILABLE ) == -1 ) {
    this.$element().html( "invalid gametype: " + gametype );
    return;
  }

  $.get('/last_matches' + (gametype ? "/" + gametype : "") + ".json")
  .done( function( data ) {
    self.render('templates/index.html', {list: data.matches}).replace( self.$element() );
  });
}

function renderQLNickname(nickname) {
  nickname = ['0', '1', '2', '3', '4', '5', '6', '7'].reduce(function(sum, current) {
    return sum.split("^" + current).join('</span><span class="qc' + current + '">');
  }, nickname);
  return '<span class="qc7">' + nickname + '</span>';
}

var app = $.sammy("#content", function() {

  this.use(Sammy.Template, 'html');

  this.notFound = function(method, path) {
    this.$element().html("404 - " + path);
  };

  this.get('#/', drawLastMatches);
  
  this.get('#/ratings/:gametype', drawRatings);
  this.get('#/ratings/:gametype/', drawRatings);
  this.get('#/ratings/:gametype/:page', drawRatings);

  this.get('#/player/:steam_id/:gametype', drawPlayerInfo);

  this.get('#/last_matches/:gametype', drawLastMatches);

  this.get('', drawLastMatches);
});

google.charts.load('current', {'packages':['corechart']});
google.charts.setOnLoadCallback( function() {
  app.run('#/');
});


