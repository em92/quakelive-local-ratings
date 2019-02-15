# -*- coding: utf-8 -*-

from app import App
from conf import settings as cfg
from submission import submit_match  # TODO: перенеси в этот блупринт

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.requests import Request

from exceptions import MatchAlreadyExists

bp = App()


@bp.exception_handler(MatchAlreadyExists)
def handle_match_already_exists_exception(request: Request, e: MatchAlreadyExists):
    raise HTTPException(409, str(e))


@bp.route("/submit", methods=["POST"])
async def http_stats_submit(request: Request):
    # https://github.com/PredatH0r/XonStat/blob/cfeae1b0c35c48a9f14afa98717c39aa100cde59/feeder/feeder.node.js#L989
    if request.headers.get("X-D0-Blind-Id-Detached-Signature") != "dummy":
        raise HTTPException(403, "signature header invalid or not found")

    if request.client.host not in ['::ffff:127.0.0.1', '::1', '127.0.0.1', 'testclient']:
        raise HTTPException(403, "non-loopback requests are not allowed")

    match_report = await request.body()
    result = submit_match(match_report.decode('utf-8'))
    if result["ok"] == False:
        raise HTTPException(422, result["message"])
    else:
        if cfg['run_post_process'] == False:
            raise HTTPException(202, result["message"])
        else:
            return JSONResponse(result)
