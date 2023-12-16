from asyncpg import Connection
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from qllr.endpoints import Endpoint

from .methods import export


class ExportRatingCommon(Endpoint):
    async def get_data(self, con: Connection, gametype_id: int):
        return await export(con, gametype_id)


class ExportRatingJson(ExportRatingCommon):
    async def get_document(self, request: Request, con: Connection) -> Response:
        data = await self.get_data(con, request.path_params["gametype_id"])
        return JSONResponse(data)


class ExportRatingCsv(ExportRatingCommon):
    async def get_document(self, request: Request, con: Connection) -> Response:
        data = await self.get_data(con, request.path_params["gametype_id"])

        result = ""

        # TODO: используй "join" сразу ибо быстрее
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
        resp.headers["Content-Type"] = "text/csv; charset=UTF-8"
        return resp


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


routes = [
    Route("/{gametype}.json", endpoint=ExportRatingJson),
    Route("/{gametype}.csv", endpoint=ExportRatingCsv),
    Route("/{frmt}/{gametype}", endpoint=ExportRatingsOldRoute),
]
