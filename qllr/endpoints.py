# -*- coding: utf-8 -*-

from calendar import timegm
from email.utils import formatdate, parsedate
from time import gmtime
from typing import Optional, Tuple

from asyncpg import Connection
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from .db import cache, get_db_pool


class Endpoint(HTTPEndpoint):
    last_req_time = None
    last_mod_time = None

    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        if self.last_req_time is None:
            return

        last_modified = self.get_last_site_modified(request)

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
        if request.path_params and "gametype" in request.path_params:
            gametype = request.path_params["gametype"] = request.path_params[
                "gametype"
            ].lower()
            if gametype not in cache.GAMETYPE_IDS:
                raise HTTPException(404, "invalid gametype: {}".format(gametype))
            else:
                request.path_params["gametype_id"] = cache.GAMETYPE_IDS[gametype]

        self.last_req_time = parsedate(request.headers.get("if-modified-since"))
        if self.last_req_time:
            self.last_req_time = self.last_req_time[0:6]

        resp = self.try_very_fast_response(request)
        if resp:
            return resp

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

    def get_last_site_modified(self, request: Request) -> Tuple:
        if 'gametype' in request.path_params:
            r = cache.LAST_GAME_TIMESTAMPS[request.path_params["gametype"]]
        else:
            # TODO: move it to cache.LAST_GAME_TIMESTAMP
            r = max(cache.LAST_GAME_TIMESTAMPS.values())
        return gmtime(r)[0:6]

    async def get_last_doc_modified(self, request: Request, con: Connection) -> Tuple:
        if self.last_mod_time:
            return self.last_mod_time

        self.last_mod_time = await self._get_last_doc_modified(request, con)
        return self.last_mod_time

    async def get_common_response(self, request: Request, con: Connection) -> Response:
        resp = await self._get(request, con)
        resp.headers["Last-Modified"] = formatdate(
            timegm(await self._get_last_doc_modified(request, con)), usegmt=True
        )
        return resp

    async def _get(self, request: Request, con: Connection) -> Response:
        raise NotImplementedError

    async def _get_last_doc_modified(self, request: Request, con: Connection) -> Tuple:
        return self.get_last_site_modified(request)
