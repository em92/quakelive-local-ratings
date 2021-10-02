import json

import starlette.convertors as cm
from asyncpg import Connection
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from qllr.endpoints import Endpoint


class GetPlayerSummaries(Endpoint):
    def try_very_fast_response(self, request: Request):
        steam_ids = request.query_params.get("steamids")
        if steam_ids:
            request.state.steam_ids = cm.CONVERTOR_TYPES["steam_ids"].convert(steam_ids)
        else:
            raise HTTPException(400, "Required parameter 'steamids' is missing")
        super().try_very_fast_response(request)

    async def get_document(self, request: Request, con: Connection) -> Response:
        await con.set_type_codec(
            "json", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
        )

        query = """
        SELECT
            json_agg(json_build_object(
                'personaname', p.name,
                'steamid',     p.steam_id
            ) ORDER by p.steam_id)
        FROM
            players p
        WHERE
            p.steam_id = ANY($1)
        """

        return JSONResponse(
            {
                "response": {
                    "players": await con.fetchval(query, request.state.steam_ids)
                },
            }
        )


routes = [Route("/GetPlayerSummaries/", endpoint=GetPlayerSummaries)]
