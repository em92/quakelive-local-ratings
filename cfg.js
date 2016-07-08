var fs = require("fs");
var path = require("path");
var url = require("url");

var default_cfg = {
  "db_url": "mongodb://localhost:27017/quakelive-local-ratings",
  "player_count_per_page": 10,
  "httpd_port": 7081,
  "run_post_process": true,
  "moving_average_count": 50
};
var allowed_param_names = Object.keys(default_cfg);
var cfg = {};
var argv = process.argv.slice(2);
var cfg_filename = argv[0] ? argv[0] : "./cfg.json";

var load = function() {
  
  var use_default = function( message, param_name ) {
    console.log(message + ". Using default " + param_name);
    cfg[ param_name ] = default_cfg[ param_name ];
  };
  
  var use_default_if_not_uint = function( param_name ) {
    try {
      if (typeof(cfg[ param_name ]) == "undefined") throw new Error(param_name + " is undefined");
      if (typeof(cfg[ param_name ]) != "number")    throw new Error(param_name + " is not a number");
      if (cfg[ param_name ] % 1 !== 0)              throw new Error(param_name + " is not a integer");
      if (cfg[ param_name ] < 0)                    throw new Error(param_name + " is not a unsigned integer");
      if (cfg[ param_name ] == 0)                   throw new Error("zero value for " + param_name + " is not allowed");
    } catch (e) {
      use_default( e.message, param_name );
    }
  };
  
  var use_default_if_not_bool = function( param_name ) {
    try {
      if (typeof(cfg[ param_name ]) == "undefined") throw new Error(param_name + " is undefined");
      if (typeof(cfg[ param_name ]) != "boolean")   throw new Error(param_name + " is not boolean");
    } catch (e) {
      use_default( e.message, param_name );
    }
  };
  
  // reading and parsing from file
  try {
    var filedata = fs.readFileSync(cfg_filename, 'UTF-8');
    cfg = JSON.parse( filedata );
  } catch(e) {
    console.log("Coudn't load " +  cfg_filename + ". Reason: " + e.message);
    console.log("Using default cfg...");
    cfg = default_cfg;
  }
  
  // removing unused params
  for (var i in cfg) {
    if (typeof(default_cfg[i]) == "undefined") {
      console.log("Unknown param: " + i.toString() + ". Skipping...")
      delete cfg[i];
    }
  }
  
  // checking individual params
  try {
    if (cfg['db_url']) {
      var url_data = url.parse(cfg['db_url']);
      if (url_data.protocol != "mongodb:")
        throw new Error("invalid protocol: " + url_data.protocol)
      
      var is_invalid_path = /[‘“'"!#$%&+^<=>?/\`]/.test( url_data.path.substring(1) );
      if (is_invalid_path)
        throw new Error("invalid path: " + url_data.path);
    } else use_default( "db_url is undefined", 'db_url' );
  } catch(e) {
    use_default( e.message, 'db_url' );
  }
  
  use_default_if_not_uint( 'httpd_port' );
  use_default_if_not_uint( 'player_count_per_page' );
  use_default_if_not_uint( 'moving_average_count' );
  use_default_if_not_bool( 'run_post_process' );
};

try {
  load();
  console.log("config:");
  console.log(cfg);
} catch (e) {
  console.error(e.message);
  process.exit(1);
}

module.exports = cfg;

// So much code why?
// http://web.archive.org/web/20090117065815/http://cwe.mitre.org/top25/
// CWE-20: Improper Input Validation 
