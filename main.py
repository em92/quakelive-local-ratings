#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uvicorn

from qllr import app
from qllr.settings import HOST, PORT

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, lifespan="on")
