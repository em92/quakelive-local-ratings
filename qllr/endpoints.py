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
from .settings import CACHE_HTTP_RESPONSE


class BaseEndpoint(HTTPEndpoint):
    async def _get(self, request: Request) -> Response:
        raise HTTPException(501)  # pragma: nocover

    async def get(self, request: Request) -> Response:
        # check for valid gametype
        if request.path_params and "gametype" in request.path_params:
            gametype = request.path_params["gametype"] = request.path_params[
                "gametype"
            ].lower()
            if gametype not in cache.GAMETYPE_IDS:
                raise HTTPException(404, "invalid gametype: {}".format(gametype))

            request.path_params["gametype_id"] = cache.GAMETYPE_IDS[gametype]

        return await self._get(request)


class NoCacheEndpoint(BaseEndpoint):
    async def _get(self, request: Request) -> Response:
        dbpool = await get_db_pool()
        con = await dbpool.acquire()
        tr = con.transaction()
        await tr.start()

        try:
            return await self.get_document(request, con)
        finally:
            await tr.rollback()
            await dbpool.release(con)


class Endpoint(BaseEndpoint):
    def try_very_fast_response(self, request: Request) -> Optional[Response]:
        if not CACHE_HTTP_RESPONSE:
            return None

        if request.state.if_mod_since is None:
            return None

        last_modified = self.get_last_doc_modified_without_db(request)

        if request.state.if_mod_since >= last_modified:
            return request.state.fast_response

        return None

    async def try_fast_response(
        self, request: Request, conn: Connection
    ) -> Optional[Response]:
        if not CACHE_HTTP_RESPONSE:
            return

        if request.state.if_mod_since is None:
            return

        last_modified = await self.get_last_doc_modified(request, conn)
        if last_modified is None:
            return

        if request.state.if_mod_since >= last_modified:
            return request.state.fast_response

    async def _get(self, request: Request) -> Response:
        # TODO: request.url is NOT relative
        cached_response_key = str(request.url)
        cached_response = cache.store.get(cached_response_key)

        if cached_response and request.headers.get("if-modified-since") is None:
            request.state.fast_response = cached_response
            cache_response_last_doc_modified = cached_response.headers["Last-Modified"]
        else:
            request.state.fast_response = Response(None, 304)
            cache_response_last_doc_modified = None

        request.state.doc_mod_time = None
        request.state.if_mod_since = parsedate(
            request.headers.get("if-modified-since", cache_response_last_doc_modified)
        )
        if request.state.if_mod_since:
            request.state.if_mod_since = request.state.if_mod_since[0:6]

        resp = self.try_very_fast_response(request)
        if resp:
            return resp

        resp = self.get_document_without_db(  # pylint: disable=assignment-from-none
            request
        )
        if resp:
            return resp

        dbpool = await get_db_pool()
        con = await dbpool.acquire()
        tr = con.transaction()
        await tr.start()

        try:
            resp = await self.try_fast_response(request, con)
            if resp:
                return resp

            resp = await self.get_document(request, con)
            resp.headers["Last-Modified"] = formatdate(
                timegm(await self.get_last_doc_modified(request, con)), usegmt=True
            )
            cache.store[cached_response_key] = resp
            return resp
        finally:
            await tr.rollback()
            await dbpool.release(con)

    def get_last_doc_modified_without_db(  # pylint: disable=no-self-use
        self, request: Request
    ) -> Tuple:
        gametype = request.path_params.get("gametype")
        r = cache.LAST_GAME_TIMESTAMP(gametype)
        return gmtime(r)[0:6]

    async def get_last_doc_modified(  # pylint: disable=unused-argument
        self, request: Request, con: Connection
    ) -> Tuple:
        return self.get_last_doc_modified_without_db(request)

    def get_document_without_db(  # pylint: disable=no-self-use,unused-argument
        self, request: Request
    ) -> Optional[Response]:
        return None

    async def get_document(self, request: Request, con: Connection) -> Response:
        raise HTTPException(501)  # pragma: nocover
