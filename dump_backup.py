#!/usr/bin/python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

parser = argparse.ArgumentParser()
parser.add_argument("-c", metavar="config.json", help="use the provided config file", default = "cfg.json")
args = parser.parse_args()

from conf import settings as cfg
if not cfg.read_from_file( args.c ):
  sys.exit(1)

if __name__ == "__main__":
  sys.exit( os.system("pg_dump {0} --no-owner -v | gzip > {1}_`date +%Y-%m-%d_%H-%M`.gz".format(
    cfg['db_url'],
    cfg['db_url'].split('/')[-1]
  )))
