# -*- coding: utf-8 -*-

from app import App
from asyncpg import Connection
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.requests import Request
from endpoints import Endpoint
from .methods import export

bp = App()


class ExportRatingCommon(Endpoint):
    async def get_data(self, con: Connection, gametype_id: int):
        return await export(con, gametype_id)


@bp.route("/{gametype}.json")
class ExportRatingJson(ExportRatingCommon):
    async def _get(self, request: Request, con: Connection) -> Response:
        data = await self.get_data(con, request.path_params['gametype_id'])
        return JSONResponse(data)


@bp.route("/{gametype}.csv")
class ExportRatingCsv(ExportRatingCommon):
    async def _get(self, request: Request, con: Connection) -> Response:
        data = await self.get_data(con, request.path_params['gametype_id'])

        result = ""

        for row in data["response"]:
            result += ";".join(
                [row["name"], str(row["rating"]), str(row["n"]), 'http://qlstats.net/player/' + row["_id"]]) + "\n"

        resp = Response(result)
        resp.headers["Content-Disposition"] = "attachment; filename=" + request.path_params['gametype'] + "_ratings.csv"
        resp.headers["Content-Type"] = "text/csv"
        return resp


@bp.route("/{frmt}/{gametype}")
class ExportRatingsOldRoute(Endpoint):
    async def get(self, request: Request):
        self.try_very_fast_response(request)

        frmt = request.path_params['frmt'].lower().strip()
        gametype = request.path_params['gametype']

        if frmt == "csv":
            return RedirectResponse(request.url_for('ExportRatingCsv', gametype = gametype))
        if frmt == "json":
            return RedirectResponse(request.url_for('ExportRatingJson', gametype = gametype))
        else:
            raise HTTPException(404, "Invalid format: {}".format(frmt))