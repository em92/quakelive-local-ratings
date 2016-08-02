#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#

from urllib.parse import urlparse
import sys
import json

default_cfg = {
  "db_url": "mongodb://localhost:27017/quakelive-local-ratings",
  "player_count_per_page": 10,
  "httpd_port": 7081,
  "run_post_process": True,
  "moving_average_count": 50
}

try:
  cfg_filename = sys.argv[1]
except IndexError:
  cfg_filename = "./cfg.json"

cfg = {}

def load():
  global cfg

  def use_default( message, param_name ):
    print( message + ". Using default " + param_name );
    cfg[ param_name ] = default_cfg[ param_name ]


  def use_default_if_not_uint( param_name ):
    try:
      if type( cfg[ param_name ] ) is None:
        raise Exception( param_name + " is null " )
      if type( cfg[ param_name ] ) is not int:
        raise Exception( param_name + " is not integer" )
      if cfg[ param_name ] < 0:
        raise Exception( param_name + " is not unsigned integer" )
      if cfg[ param_name ] == 0:
        raise Exception( "zero value for " + param_name + " is not allowed" )
    except KeyError:
      use_default( param_name + " is undefined", param_name )
    except Exception as e:
      use_default( type(e).__name__ + ": " + str(e), param_name )


  def use_default_if_not_bool( param_name ):
    try:
      if type( cfg[ param_name ] ) is None:
        raise Exception( param_name + " is null " ) 
      if type( cfg[ param_name ] ) is not bool:
        raise Exception( param_name + " is not boolean" )
    except KeyError:
      use_default( param_name + " is undefined", param_name )
    except Exception as e:
      use_default( type(e).__name__ + ": " + str(e), param_name )

  # reading and parsing from file
  try:
    f = open(cfg_filename, "r")
    cfg = json.load( f )
    f.close()
  except Exception as e:

    print("Coudn't load " +  cfg_filename + ". Reason: " + str(e));
    print("Using default cfg...");
    cfg = default_cfg;

  # removing usused params
  for key, value in cfg.copy().items():
    if key not in default_cfg.keys():
      del cfg[key]

  # checking individual params
  try:
    url_data = urlparse( cfg['db_url'] )
    if url_data.scheme != "mongodb":
      raise Exception( "invalid protocol: " + url_data.scheme )

    is_invalid_path = any( c in url_data.path[1:] for c in "‘“'\"!#$%&+^<=>?/\`" )
    if is_invalid_path:
      raise Exception( "invalid path: " + url_data.path )

  except KeyError:
    use_default( param_name + " is undefined", param_name )
  except Exception as e:
    use_default( type(e).__name__ + ": " + str(e), 'db_url' )

  use_default_if_not_uint( 'httpd_port' );
  use_default_if_not_uint( 'player_count_per_page' );
  use_default_if_not_uint( 'moving_average_count' );
  use_default_if_not_bool( 'run_post_process' );


try:
  load()
  print("config:")
  for key, value in cfg.items():
    print(key, ":\t", value)
except Exception as e:
  print(e, file=sys.stderr)
  sys.exit(1)

# So much code why?
# http://web.archive.org/web/20090117065815/http://cwe.mitre.org/top25/
