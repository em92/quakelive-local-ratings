#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys

from qllr.settings import DATABASE_URL

parser = argparse.ArgumentParser()
parser.add_argument("filename", help="use provided backup file")
args = parser.parse_args()


if __name__ == "__main__":
    sys.exit(
        os.system("gunzip -c {1} | psql -d {0}".format(DATABASE_URL, args.filename))
    )
