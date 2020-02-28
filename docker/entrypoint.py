#!/usr/bin/env python3

import os
import socket
import sys

from os import environ
from time import sleep
from urllib.parse import urlparse

DATABASE_URL = None
try:
    DATABASE_URL = environ["DATABASE_URL"]
except KeyError:
    print("DATABASE_URL not defined as enviroment variable", file=sys.stderr)
    envfile = os.path.dirname(os.path.realpath(__file__)) + "/../.env"
    print("Trying to read from {}".format(envfile), file=sys.stderr)
    with open(envfile) as f:
        for line in f:
            if line.startswith("DATABASE_URL"):
                _, DATABASE_URL = line.strip().split('=', 1)

if not DATABASE_URL:
    print("DATABASE_URL not defined", file=sys.stderr)
    sys.exit(1)

o = urlparse(DATABASE_URL)
host = o.hostname
port = o.port or 5432

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
for i in range(10):
    try:
        s.connect((host, port))
        s.shutdown(socket.SHUT_RDWR)
        sys.exit(0)
    except Exception as e:
        print(e, file=sys.stderr)
        sleep(1)

print("Could not connect to {}:{}".format(host, port), file=sys.stderr)
sys.exit(1)
