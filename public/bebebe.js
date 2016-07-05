var RatingList = React.createClass({
  
  getInitialState: function() {
    return { list: [], gametype: "", page: 0, page_count: 0, loading: false, error: false };
  },
  
  downloadList: function(gametype, page) {
    var self = this;
    
    $.get( "rating/" + gametype + "/" + page.toString(), function( data ) {
      if (data.ok == false) {
        self.setState({error: data.message});
        return;
      };
      
      self.setState({list: data.response, gametype: gametype, page: page, page_count: data.page_count, loading: false, error: false});
    });
  },
  
  renderQLNickname: function(nickname) {
    nickname = ['1', '2', '3', '4', '5', '6', '7'].reduce(function(sum, current) {
      return sum.split("^" + current).join('</span><span class="qc' + current + '">');
    }, nickname);
    return '<span class="qc7">' + nickname + '</span>';
  },
  
  componentWillMount: function() {
    this.downloadList(this.props.gametype, this.props.page);
  },
  
  componentWillReceiveProps: function(nextProps) {
    this.downloadList(nextProps.gametype, nextProps.page);
  },
  
  render: function() {
    var self = this;
    
    if (this.state.loading == true) {
      return React.createElement("p", null, "Loading...");
    }
    
    if (this.state.error) {
      return React.createElement("p", null, "Error: " + this.state.error);
    }
    
    var pageLinks = [];
    for(var i=0; i<this.state.page_count; i++) {
      if (i == this.state.page) {
        pageLinks.push(React.createElement("span", {key: i}, "[" + (i+1) + "]"));
      } else {
        pageLinks.push(React.createElement("a", {href: "#!/ratings/" + this.state.gametype + "/" + i, key: i}, "[" + (i+1) + "]"));
      }
    }
    
    var result = this.state.list.map(function(item, i) {
      return React.createElement('tr', {key: i}, 
        React.createElement('td', {className: 'col-md-1'}, item.rank),
        React.createElement('td', {className: 'col-md-3'}, 
          React.createElement('a', {href: 'http://steamcommunity.com/profiles/' + item._id + '/', dangerouslySetInnerHTML: {__html: self.renderQLNickname(item.name)} })
        ),
        React.createElement('td', {className: 'col-md-1'}, item.rating),
        React.createElement('td', {className: 'col-md-1'}, item.n)
      )
    });
    
    return React.createElement('div', {id: "summary-table-wrapper"} ,
      React.createElement('table', {id: "summary-table", className: "table table-borderless"},
        React.createElement('thead', null, React.createElement('tr', null,  
          React.createElement('th', null, "Rank"),
          React.createElement('th', null, "Nickname"),
          React.createElement('th', null, "Rating"),
          React.createElement('th', null, "Match Count")
        )),
        React.createElement('tbody', null, result)
      ),
      React.createElement("span", null, pageLinks)
    );
  }
});

var PlayerInfo = React.createClass({

  getInitialState: function() {
    return { loading: true, error: false };
  },
  
  downloadData: function(player_id, gametype) {
    var self = this;
    
    if ( (typeof(gametype) == 'undefined') || (gametype == "")  ){
      self.setState({error: "gametype is NOT set"});
      return;
    }
    self.setState({loading: true});
      
    $.get( "player/" + player_id.toString(), function( data ) {
      if (data.ok == false) {
        self.setState({loading: false, error: data.message});
      } else {
        self.drawChart(data.player[gametype].history);
        self.setState({loading: false, error: false});
        
      }
    });
  },

  drawChart: function(history) {
    var chart = new google.visualization.ColumnChart(this.refs.chart);
    var options = {
      bar: {groupWidth: "50%"},
      explorer: { keepInBounds: true }
    };
    var data = new google.visualization.DataTable();
    data.addColumn('string', 'Date');
    data.addColumn('number', 'Rating');
    data.addRows(history.map( function (item, i) {
      return [new Date(item.timestamp*1000).toLocaleFormat('%d-%b-%Y %H:%M:%S'), item.rating];
    }));
    chart.draw(data, options);
  },  

  componentWillMount: function() {
    this.downloadData(this.props.id, this.props.gametype);
  },
  
  componentWillReceiveProps: function(nextProps) {
    this.downloadData(nextProps.id, nextProps.gametype);
  },
  
  render: function() {
    var self = this;
    
    return (<div>
      {this.state.loading ? <p>Loading</p> : null}
      {this.state.error ? <p>{this.state.error}</p> : null}
      <div ref="chart" style={{width: "900px", height: "500px"}}></div>
    </div>);
  }
});

var App = React.createClass({

  mixins: [ReactMiniRouter.RouterMixin],

  routes: {
    '/ratings/:gametype': 'ratings',
    '/ratings/:gametype/:page': 'ratings',
    '/player/:id': 'player',
    '/player/:id/:gametype': 'player',
    '/': 'home'
  },

  render: function() {
    return this.renderCurrentRoute();
  },

  home: function() {
    return React.createElement("div", null, 
      React.createElement("a", {href: "#!/ratings/ctf"}, "ctf"),
      React.createElement("br"),
      React.createElement("a", {href: "#!/ratings/tdm"}, "tdm"),
      React.createElement("br"),
      React.createElement("a", {href: "#!/ratings/ad"}, "ad")
    );
  },

  ratings: function(gametype, page) {
    page = (typeof(page) != 'string') ? 0 : parseInt(page);
    return React.createElement(RatingList, {gametype: gametype, page: page});
  },

  player: function(id, gametype) {
    return React.createElement(PlayerInfo, {id: id, gametype: gametype});
  },

  notFound: function(path) {
    return React.createElement("div", null, "Invalid path: " + path);
  }

});

google.charts.load('current', {'packages':['corechart']});
google.charts.setOnLoadCallback( function() {
  ReactDOM.render(<App />, document.getElementById('content'));
});

