#!/usr/bin/env python3

import uvicorn

from qllr import app
from qllr.settings import HOST, PORT, TRUSTED_PROXIES

if __name__ == "__main__":
    uvicorn.run(
        app, host=HOST, port=PORT, lifespan="on", forwarded_allow_ips=TRUSTED_PROXIES
    )
