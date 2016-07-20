var app = $.sammy("#content", function() {

  this.use('Template');

  this.get('#/', function(context) {
    context.render('templates/index.template.html').appendTo(context.$element());
  });

});

$(document).ready(function() {
  app.run('#/');
});


