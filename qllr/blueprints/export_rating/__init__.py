# -*- coding: utf-8 -*-

from asyncpg import Connection
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from qllr.app import App
from qllr.endpoints import Endpoint

from .methods import export

bp = App()


class ExportRatingCommon(Endpoint):
    async def get_data(self, con: Connection, gametype_id: int):
        return await export(con, gametype_id)


@bp.route("/{gametype}.json")
class ExportRatingJson(ExportRatingCommon):
    async def get_document(self, request: Request, con: Connection) -> Response:
        data = await self.get_data(con, request.path_params["gametype_id"])
        return JSONResponse(data)


@bp.route("/{gametype}.csv")
class ExportRatingCsv(ExportRatingCommon):
    async def get_document(self, request: Request, con: Connection) -> Response:
        data = await self.get_data(con, request.path_params["gametype_id"])

        result = ""

        for row in data["response"]:
            result += (
                ";".join(
                    [
                        row["name"],
                        str(row["rating"]),
                        str(row["n"]),
                        "http://qlstats.net/player/" + row["_id"],
                    ]
                )
                + "\n"
            )

        resp = Response(result)
        resp.headers["Content-Disposition"] = (
            "attachment; filename=" + request.path_params["gametype"] + "_ratings.csv"
        )
        resp.headers["Content-Type"] = "text/csv"
        return resp


@bp.route("/{frmt}/{gametype}")
class ExportRatingsOldRoute(Endpoint):
    def get_document_without_db(self, request: Request) -> Response:
        frmt = request.path_params["frmt"].lower().strip()
        gametype = request.path_params["gametype"]

        if frmt == "csv":
            return RedirectResponse(
                request.url_for("ExportRatingCsv", gametype=gametype), status_code=308
            )
        if frmt == "json":
            return RedirectResponse(
                request.url_for("ExportRatingJson", gametype=gametype), status_code=308
            )
        else:
            raise HTTPException(404, "Invalid format: {}".format(frmt))
