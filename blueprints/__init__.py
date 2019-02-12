# -*- coding: utf-8 -*-

import starlette.convertors as cm

from typing import Any
from starlette.exceptions import HTTPException


class SteamIdsConvertor(cm.Convertor):
    regex = r"[0-9+]+"

    def convert(self, value: str) -> Any:
        if not value:
            raise HTTPException(422, "No steam ids given")
        ids = value.split("+")
        bad_ids = list(filter(lambda steam_id: not steam_id.isnumeric(), ids))
        if bad_ids:
            raise HTTPException(422, "Invalid steam ids: {0}".format(", ".join(bad_ids)))
        return list(map(lambda steam_id: int(steam_id), ids))

    def to_string(self, value: Any) -> str:
        return "+".join(map(lambda item: str(item), value))


cm.CONVERTOR_TYPES['steam_ids'] = SteamIdsConvertor()

from .balance_api import bp as balance_api  # noqa: F401
