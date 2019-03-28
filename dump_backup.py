#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

from qllr.settings import DATABASE_URL

if __name__ == "__main__":
    sys.exit(
        os.system(
            "pg_dump {0} --no-owner -v | gzip > {1}_`date +%Y-%m-%d_%H-%M`.gz".format(
                DATABASE_URL, DATABASE_URL.split("/")[-1]
            )
        )
    )
