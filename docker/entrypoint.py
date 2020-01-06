#!/usr/bin/env python3

import socket
import sys

from os import environ
from time import sleep
from urllib.parse import urlparse

o = urlparse(environ["DATABASE_URL"])
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
