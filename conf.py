# -*- coding: utf-8 -*-
#

from urllib.parse import urlparse
import json

from common import logger


class Settings:
  def __init__(self):
    self._conf = {
      "db_url": "postgres://eugene:bebebe@localhost:5432/qllr",
      "player_count_per_page": 10,
      "httpd_port": 7081,
      "run_post_process": True,
      "min_player_count_in_match_to_rate_ad": 6,
      "min_player_count_in_match_to_rate_ctf": 6,
      "min_player_count_in_match_to_rate_tdm": 6,
      "min_player_count_in_match_to_rate_tdm2v2": 4,
      "moving_average_count": 50,
      "use_avg_perf_ad": False,
      "use_avg_perf_ctf": False,
      "use_avg_perf_tdm": False,
      "use_avg_perf_tdm2v2": False
    }


  @property
  def USE_AVG_PERF(self, gametype):
    try:
      return self._conf[ "use_avg_perf_{}".format( gametype.lower() ) ]
    except KeyError:
      raise KeyError("invalid gametype: {}".format(gametype))


  def __getitem__(self, index):
    return self._conf[index]


  def read_from_file(self, filename):
    with open(filename, "r") as f:
      cfg = json.load( f )

    # parsing every item
    error_count = 0
    for key, value in cfg.items():

      try:
        if key not in self._conf:
          logger.warn("ignoring key in config file: {}".format( key ))

        elif type(value) is not type(self._conf[key]):
          raise AssertionError("value of {} expected to be type of {}, but {} given".format( key, type(self._conf[key]).__name__, type(value).__name__ ))

        elif type(value) is int and not value > 0:
          raise AssertionError("value of {} expected to be greater than zero, but {} given".format( key, value ))

        elif key == 'db_url':
          url_data = urlparse( value )

          if url_data.scheme != "postgres":
            raise AssertionError("invalid protocol in db_url: {} ".format( url_data.scheme ))

          is_invalid_path = any( c in url_data.path[1:] for c in "‘“'\"!#$%&+^<=>?/\`" )
          if is_invalid_path:
            raise AssertionError("invalid path in db_url: {}".format( url_data.path ))

        self._conf[ key ] = value

      except AssertionError as e:
        logger.error( str(e) )
        error_count = error_count + 1

    return error_count == 0


settings = Settings()
