#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-c", metavar="config.json", help="use the provided config file", default = "cfg.json")
parser.add_argument("filename", help="use provided backup file")
args = parser.parse_args()

from conf import settings as cfg
if not cfg.read_from_file( args.c ):
  sys.exit(1)

if __name__ == "__main__":
  sys.exit( os.system("gunzip -c {1} | psql -d {0}".format(
    cfg['db_url'],
    args.filename
  )))
