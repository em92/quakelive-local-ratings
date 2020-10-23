from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from qllr.settings import RUN_POST_PROCESS
from qllr.submission import submit_match  # TODO: перенеси в этот блупринт


async def http_stats_submit(request: Request):
    # https://github.com/PredatH0r/XonStat/blob/cfeae1b0c35c48a9f14afa98717c39aa100cde59/feeder/feeder.node.js#L989
    if request.headers.get("X-D0-Blind-Id-Detached-Signature") != "dummy":
        raise HTTPException(403, "signature header invalid or not found")

    if request.client.host not in [
        "::ffff:127.0.0.1",
        "::1",
        "127.0.0.1",
        "testclient",
    ]:
        raise HTTPException(403, "non-loopback requests are not allowed")

    match_report = await request.body()
    result = await submit_match(match_report.decode("utf-8"))
    if RUN_POST_PROCESS is False:
        raise HTTPException(202, result["message"])

    return JSONResponse(result)


routes = [Route("/submit", endpoint=http_stats_submit, methods=["POST"])]
