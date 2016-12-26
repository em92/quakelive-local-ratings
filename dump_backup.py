#!/usr/bin/python3
# -*- coding: utf-8 -*-

from config import cfg
import os
import sys

if __name__ == "__main__":
  sys.exit( os.system("pg_dump {0} --no-owner -F t -f {1}_`date +%Y-%m-%d_%H-%M`.tar.gz -v".format(
    cfg['db_url'],
    cfg['db_url'].split('/')[-1]
  )))
