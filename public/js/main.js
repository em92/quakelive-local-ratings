var GAMETYPES_AVAILABLE = ['ad', 'ctf', 'tdm'];

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

function renderQLNickname(nickname) {
  nickname = ['1', '2', '3', '4', '5', '6', '7'].reduce(function(sum, current) {
    return sum.split("^" + current).join('</span><span class="qc' + current + '">');
  }, nickname);
  return '<span class="qc7">' + nickname + '</span>';
}

var app = $.sammy("#content", function() {

  this.use(Sammy.Template, 'html');

  this.notFound = function(method, path) {
    this.$element().html("404 - " + path);
  };

  this.get('#/', function() {
    this.render('templates/index.html').replace( this.$element() );
  });
  
  this.get('#/ratings/:gametype', drawRatings);
  this.get('#/ratings/:gametype/', drawRatings);
  this.get('#/ratings/:gametype/:page', drawRatings);

  
});

$(document).ready(function() {
  app.run('#/');
});


