# -*- coding: utf-8 -*-

from time import gmtime
from email.utils import parsedate, formatdate
from db import cache, get_db_pool
from typing import Tuple

from asyncpg import Connection
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response


class Endpoint(HTTPEndpoint):
    last_req_time = None
    last_mod_time = None

    def try_very_fast_response(self, request: Request):
        if self.last_req_time is None:
            return

        last_modified = self.get_last_site_modified()
        last_modified = gmtime(last_modified)[:]

        if self.last_req_time >= last_modified:
            raise HTTPException(304)

    async def try_fast_response(self, request: Request, conn: Connection) -> None:
        if self.last_req_time is None:
            return

        last_modified = await self.get_last_doc_modified(request, conn)
        if last_modified is None:
            return

        if self.last_req_time >= last_modified:
            raise HTTPException(304)

    async def get(self, request: Request) -> Response:
        # check for valid gametype
        if request.path_params and 'gametype' in request.path_params:
            gametype = request.path_params['gametype'] = request.path_params['gametype'].lower()
            if gametype not in cache.GAMETYPE_IDS:
                raise HTTPException(404, "invalid gametype: {}".format(gametype))
            else:
                request.path_params['gametype_id'] = cache.GAMETYPE_IDS[gametype]

        self.last_req_time = parsedate(request.headers.get("if-modified-since"))

        self.try_very_fast_response(request)

        dbpool = await get_db_pool()
        con = await dbpool.acquire()
        tr = con.transaction()
        await tr.start()

        try:
            await self.try_fast_response(request, con)
            return await self.get_common_response(request, con)
        finally:
            await tr.rollback()
            await dbpool.release(con)

    def get_last_site_modified(self, request: Request):
        if 'gametype' in request.path_params:
            return cache.LAST_GAME_TIMESTAMPS[request.path_params["gametype"]]
        else:
            # TODO: move it to cache.LAST_GAME_TIMESTAMP
            return max(cache.LAST_GAME_TIMESTAMPS.values())

    async def get_last_doc_modified(self, request: Request, con: Connection) -> Tuple:
        if self.last_mod_time:
            return self.last_mod_time

        self.last_mod_time = await self._get_last_doc_modified(request, con)
        return self.last_mod_time

    async def get_common_response(self, request: Request, con: Connection) -> Response:
        resp = await self._get(request, con)
        resp.headers['Last-Modified'] = formatdate(await self._get_last_doc_modified(request, con), usegmt=True)
        return resp

    async def _get(self, request: Request, con: Connection) -> Response:
        raise NotImplementedError

    async def _get_last_doc_modified(self, request: Request, con: Connection) -> Tuple:
        return self.get_last_site_modified(request)
