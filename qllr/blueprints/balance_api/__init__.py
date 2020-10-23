from typing import Optional

from asyncpg import Connection
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from qllr.endpoints import Endpoint

from .methods import fetch

# TODO: json only return


class BalanceCommon(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        return JSONResponse(await fetch(con, ids))


class BalanceAdvanced(Endpoint):
    async def get_document(self, request: Request, con: Connection):
        ids = request.path_params["ids"]
        options = request.path_params["options"]

        # TODO: implement with_qlstats_policy
        #  also try_very_fast_response and try_fast_respone must return none
        return JSONResponse(
            await fetch(
                con,
                ids,
                mapname=request.headers.get("X-QuakeLive-Map")
                if "map_based" in options
                else None,
                bigger_numbers="bn" in options,
                with_qlstats_policy=True if "with_qlstats_policy" in options else False,
            )
        )


routes = [
    Route("/{ids:steam_ids}", endpoint=BalanceCommon),
    Route("/{options:balance_options}/{ids:steam_ids}", endpoint=BalanceAdvanced),
]
