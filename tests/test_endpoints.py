from pytest import fixture, mark, param, raises
from starlette.testclient import TestClient

from qllr.app import App, JSONResponse, PlainTextResponse, Request
from qllr.db import Connection
from qllr.endpoints import Endpoint


@fixture(scope="module")
def test_cli_with_endpoint(test_cli):
    app = App()
    app.counter = 0

    @app.route("/get_document")
    class Sample(Endpoint):
        async def get_document(self, request: Request, con: Connection):
            app.counter = app.counter + 1
            return JSONResponse({"counter": app.counter})

    @app.route("/get_document_without_db")
    class Sample(Endpoint):
        def get_document_without_db(self, request: Request):
            app.counter = app.counter + 1
            return JSONResponse({"counter": app.counter})

    @app.route("/gametype/{gametype}")
    class Sample(Endpoint):
        def get_document_without_db(self, request: Request):
            return PlainTextResponse(request.path_params["gametype"])

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_get_document_cache(test_cli_with_endpoint):
    expected_value = test_cli_with_endpoint.get("/get_document").json()["counter"]
    # response is cached, so expecting same value
    assert test_cli_with_endpoint.get("/get_document").json() == {
        "counter": expected_value
    }


def test_get_document_without_db_no_cache(test_cli_with_endpoint):
    expected_value = test_cli_with_endpoint.get("/get_document_without_db").json()[
        "counter"
    ]
    # not expecting response to be cached, if not accessing db
    assert test_cli_with_endpoint.get("/get_document_without_db").json() == {
        "counter": expected_value + 1
    }


@mark.parametrize(
    "input_gametype,output_gametype",
    [param("AD", "ad"), param("CtF", "ctf"), param("tdm", "tdm")],
)
def test_valid_gametype_check(test_cli_with_endpoint, input_gametype, output_gametype):
    test_cli_with_endpoint.get("/gametype/{}".format(input_gametype))


def test_invalid_gametype_check(test_cli_with_endpoint):
    resp = test_cli_with_endpoint.get(
        "/gametype/{}".format("this_gametype_does_not_exist")
    )
    assert resp.status_code == 404
