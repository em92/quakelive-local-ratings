#!/usr/bin/python3
# -*- coding: utf-8 -*-

from config import cfg
import os
import sys

if __name__ == "__main__":
  sys.exit( os.system("pg_restore -n public -d {0} {1} -v".format(
    cfg['db_url'],
    sys.argv[1]
  )))
