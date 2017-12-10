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


def clean_name(name):
  for s in ['0', '1', '2', '3', '4', '5', '6', '7']:
    name = name.replace("^" + s, "")

  if name == "":
    name = "unnamed"

  return name
