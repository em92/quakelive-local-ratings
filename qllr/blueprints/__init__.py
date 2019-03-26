# -*- coding: utf-8 -*-

import starlette.convertors as cm

from typing import Any
from uuid import UUID
from starlette.exceptions import HTTPException


class SteamIdsConvertor(cm.Convertor):
    regex = r"[0-9+\ ,]+"

    def convert(self, value: str) -> Any:
        if not value:
            raise HTTPException(422, "No steam ids given")
        ids = value.replace(" ", "+").replace(",", "+").split("+")
        bad_ids = list(filter(lambda steam_id: not steam_id.isnumeric(), ids))
        if bad_ids:
            raise HTTPException(422, "Invalid steam ids: {0}".format(", ".join(bad_ids)))
        return list(map(lambda steam_id: int(steam_id), ids))

    def to_string(self, value: Any) -> str:
        return "+".join(map(lambda item: str(item), value))


class MatchIdConvertor(cm.Convertor):
    regex = r"[0-9A-Fa-f\-]+"

    def convert(self, value: str) -> Any:
        try:
            if len(value) != len('12345678-1234-5678-1234-567812345678'):
                raise ValueError()
            UUID(value)
        except ValueError:
            raise HTTPException(422, "Invalid match id")

        return value

    def to_string(self, value: Any) -> str:
        return value


cm.CONVERTOR_TYPES['steam_ids'] = SteamIdsConvertor()
cm.CONVERTOR_TYPES['match_id'] = MatchIdConvertor()

from .balance_api import bp as balance_api  # noqa: F401
from .export_rating import bp as export_rating  # noqa: F401
from .matches import bp as matches  # noqa: F401
from .player import bp as player  # noqa: F401
from .ratings import bp as ratings
from .submission import bp as submission  # noqa: F401
from .scoreboard import bp as scoreboard  # noqa: F401
from .steam_api import bp as steam_api  # noqa: F401
from .deprecated import bp as deprecated  # noqa: F401
