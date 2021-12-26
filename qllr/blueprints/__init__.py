# isort:skip_file

from typing import Any
from uuid import UUID

import starlette.convertors as cm
from starlette.exceptions import HTTPException


class SteamIdsConvertor(cm.Convertor):
    regex = r"[0-9+\ ,]+"

    def convert(self, value: str) -> Any:
        if not value:
            raise HTTPException(422, "No steam ids given")
        ids = value.replace(" ", "+").replace(",", "+").split("+")
        bad_ids = list(filter(lambda steam_id: not steam_id.isnumeric(), ids))
        if bad_ids:
            raise HTTPException(
                422, "Invalid steam ids: {0}".format(", ".join(bad_ids))
            )
        return list(map(int, ids))

    def to_string(self, value: Any) -> str:
        return "+".join(map(str, value))


class MatchIdConvertor(cm.Convertor):
    regex = r"[0-9A-Fa-f\-]+"

    def convert(self, value: str) -> Any:
        try:
            if len(value) != len("12345678-1234-5678-1234-567812345678"):
                raise ValueError()
            UUID(value)
        except ValueError:
            raise HTTPException(422, "Invalid match id")

        return value

    def to_string(self, value: Any) -> str:
        return value


class BalanceOptionsConvertor(cm.Convertor):
    regex = r"[A-Za-z_,]+"

    def convert(self, value: str) -> Any:
        result = set(value.lower().split(","))
        valid_options = set(["bn", "map_based", "with_qlstats_policy"])
        invalid_options = ", ".join(list(result.difference(valid_options)))
        if invalid_options:
            raise ValueError("invalid options: {}".format(invalid_options))
        return result

    def to_string(self, value: Any) -> str:
        return ",".join(list(value))


cm.CONVERTOR_TYPES["steam_ids"] = SteamIdsConvertor()
cm.CONVERTOR_TYPES["match_id"] = MatchIdConvertor()
cm.CONVERTOR_TYPES["balance_options"] = BalanceOptionsConvertor()

from . import balance_api  # noqa: F401
from . import deprecated  # noqa: F401
from . import export_rating  # noqa: F401
from . import matches  # noqa: F401
from . import player  # noqa: F401
from . import ratings  # noqa: F401
from . import scoreboard  # noqa: F401
from . import steam_api  # noqa: F401
from . import submission  # noqa: F401
