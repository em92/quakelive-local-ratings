# -*- coding: utf-8 -*-

from time import gmtime
from email.utils import parsedate
from db import cache, get_db_pool
from typing import Tuple, Optional

from asyncpg import Connection
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import Message, Receive, Scope, Send


class Endpoint(HTTPEndpoint):
    last_req_time = None

    def try_very_fast_response(self, request: Request):
        last_req_time = self.last_req_time

        if 'gametype' in request.path_params:
            last_modified = cache.LAST_GAME_TIMESTAMPS[request.path_params["gametype"]]
        else:
            # TODO: move it to cache.LAST_GAME_TIMESTAMP
            last_modified = max(cache.LAST_GAME_TIMESTAMPS.values())

        last_modified = gmtime(last_modified)[:]

        if last_req_time >= last_modified:
            raise HTTPException(304)

    async def try_fast_response(self, request: Request, conn: Connection) -> None:
        last_req_time = self.last_req_time

        last_modified = await self.get_last_modified(request, conn)
        if last_modified is None:
            return

        if last_req_time >= last_modified:
            raise HTTPException(304)

    async def get(self, request: Request) -> Response:
        # check for valid gametype
        if request.path_params and 'gametype' in request.path_params:
            request.path_params['gametype'] = request.path_params['gametype'].lower()
            if request.path_params['gametype'] not in cache.GAMETYPE_IDS:
                raise HTTPException(404, "invalid gametype: {}".format(request.path_params['gametype']))

        last_req_time = parsedate(request.headers["if-modified-since"])
        if last_req_time is not None:
            self.last_req_time = last_req_time

            self.try_very_fast_response(request)

            dbpool = await get_db_pool()
            con = await dbpool.acquire()
            with con.transaction():
                await self.try_fast_response(request, con)
                return await self.get_common_response(request, con)
        else:
            dbpool = await get_db_pool()
            con = await dbpool.acquire()
            with con.transaction():
                return await self.get_common_response(request, con)

    async def get_last_modified(self, request: Request, conn: Connection) -> Optional[Tuple]:
        return None

    async def get_common_response(self, request: Request, conn: Connection) -> Response:
        resp = await self._get(request, conn)
        # TODO: use get_last_modified
        return resp

    async def _get(self, request: Request, conn: Connection) -> Response:
        raise NotImplementedError