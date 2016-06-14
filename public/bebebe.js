var RatingList = React.createClass({
  
  getInitialState: function() {
    return { list: [], page: 0, loading: false, error: false };
  },
  
  downloadPage: function(page) {
    var self = this;
    
    $.get( "rating/" + this.props.gametype + "/" + page.toString(), function( data ) {
      if (data.ok == false) {
        self.setState({error: data.message});
        return;
      };
      
      self.setState({list: data.response, page: page, loading: false, error: false});
    });
  },
  
  renderQLNickname: function(nickname) {
    nickname = ['1', '2', '3', '4', '5', '6', '7'].reduce(function(sum, current) {
      return sum.split("^" + current).join('</span><span class="qc' + current + '">');
    }, nickname);
    return '<span class="qc7">' + nickname + '</span>';
  },
  
  componentDidMount: function() {
    this.downloadPage(0);
  },
  
  render: function() {
    var self = this;
    
    console.log(this.state);
    
    if (this.state.loading == true) {
      return React.createElement("p", null, "Loading...");
      console.log("hhhh");
    }
    
    if (this.state.error) {
      return React.createElement("p", null, "Error: " + this.state.error);
    }
    
    console.log(this.state);
    var result = this.state.list.map(function(item, i) {
      return React.createElement('tr', {key: i}, 
        React.createElement('td', {className: 'col-md-1'}, item.rank),
        React.createElement('td', {className: 'col-md-3', dangerouslySetInnerHTML: {__html: self.renderQLNickname(item.name)}}),
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
      )
    );
  }
});
