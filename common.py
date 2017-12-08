# -*- coding: utf-8 -*-
#

import logging

logger = logging.getLogger("qllr")
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', "%Y-%m-%d %H:%M:%S")
ch.setFormatter(formatter)

logger.addHandler(ch)
