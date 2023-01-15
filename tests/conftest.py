import asyncio
import json
import os
import typing

import psycopg2
from pytest import fixture
from requests import Response
from starlette.config import environ
from starlette.testclient import TestClient
from testing import postgresql as pgsql_test

postgresql = None
module_path = os.path.dirname(os.path.realpath(__file__))


def pytest_configure(config):
    def handler(postgresql):
        f = open(os.path.dirname(os.path.realpath(__file__)) + "/../sql/init.sql")
        sql_query = f.read()
        f.close()
        conn = psycopg2.connect(**postgresql.dsn())
        cursor = conn.cursor()
        cursor.execute(sql_query)
        cursor.close()
        conn.commit()
        conn.close()

    global postgresql
    # force default timezone to pass tests on os with different local timezone setting
    pgsql_test.Postgresql.DEFAULT_SETTINGS["postgres_args"] += " -c timezone=+5"

    PGSQLFactory = pgsql_test.PostgresqlFactory(
        cache_initialized_db=True, on_initialized=handler
    )

    postgresql = PGSQLFactory()
    environ["DATABASE_URL"] = postgresql.url()
    environ["USE_AVG_PERF_TDM"] = "TRUE"
    environ["CACHE_HTTP_RESPONSE"] = "1"


def read_sample(sample_filename: str) -> str:
    with open(module_path + "/samples/" + sample_filename, "rb") as f:
        result = f.read()
    return result.decode("utf-8")


def read_json_sample(sample_filename: str) -> typing.Dict:
    return json.loads(read_sample(sample_filename + ".json"))


class Service:
    def __init__(self, test_cli):
        self._test_cli = test_cli

        cases = (
            ("sample01", "69770ca5-943c-491d-931e-720c5474d33b"),
            ("sample02", "44c479b9-fdbd-4674-b5bd-a56ef124e48c"),
            ("sample03", "abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4"),
            ("sample04", "125f1bda-5502-4549-b5e7-4e4ab01386df"),
            ("sample05", "7d5b863f-ee71-4f74-b237-c9f743f14976"),
            ("sample06", "fddd7e05-6a1e-462c-aed1-7af81177d483"),
            ("sample07", "52b7ae54-8040-4a21-9912-9e5ee13e2caa"),
            ("sample08", "87dfda21-423e-4f6b-89f3-eefbfba1dff0"),
            ("sample09", "5185e664-e476-49ba-953d-a6d59080d50b"),
            ("sample10", "0ff2772c-e609-4368-b21f-6dffa0b898fb"),
            ("sample11", "6ba4f41b-17bd-45dc-883e-9dacb49f3092"),
            ("sample12", "93a0b31f-4326-4971-ae51-8ddd97b74b83"),
            ("sample13", "8b59128f-600f-4e34-a733-6ce82a22cd6d"),
            ("sample14", "39ac0a42-55a6-44b4-ac06-69571db6bc31"),
            ("sample15", "e3492e13-6792-4ff6-9554-ff869c7e4931"),
            ("sample16", "c51c6bb7-9be2-455d-aef0-dcad07a9b4d1"),
            ("sample17", "dd961b26-bafe-4bd3-a515-c0ec156fd85c"),
            ("sample18", "77c4459a-90d0-4598-b399-971f278bdc38"),
            ("sample19", "47bf1f66-21a8-4414-a196-fb4262f2f81e"),
            ("sample20", "4b4ee658-0140-46ea-9d84-5bb802199400"),
            ("sample21", "13d71e4f-69e9-4a04-8c37-f12a35ab9d2f"),
            ("sample22", "61aad138-b69d-4ae7-b02e-23a9cfb7935f"),
            ("sample23", "44de3665-dd33-4f09-ae2e-a3f0456e6a9b"),
            ("sample24", "8d599bb1-6f7f-4dcf-9e95-da62f2b1a698"),
            ("sample25", "06b0c4d0-9720-40c5-92c5-e406c1496684"),
            ("sample26", "c0ac214d-b228-440b-a3fd-b5fe6ce3081d"),
            ("sample27", "55bce45b-305d-4ab4-8bbe-ec8ddc8bc037"),
            ("sample28", "a22d0122-1382-4533-bf01-403114fac08f"),
            ("sample29", "3bd7ffa1-2c35-48c8-8cb5-fe582c9684ba"),
            ("sample30", "a2a89cbc-3c6e-4430-b3eb-c32b610ad4ff"),
            ("sample31", "55ef6e6a-f7ab-4f4b-ba26-c77963147b98"),
            ("sample32", "0e463edf-12cf-4858-8739-83fe57e98e7a"),
            ("sample33", "3a3a88ed-f11e-404c-b362-d5ce376ec241"),
            ("sample34", "9cbb425a-b7a9-4376-9b1a-e68e8622f851"),
            ("sample35", "dd4ce899-ce86-4ec5-8b3e-c8303433a353"),
            ("sample36", "a53b8274-989d-4e07-afd8-3603d402b207"),
            ("sample37", "6e34afa3-a8e0-4dba-a496-3fc17e615e8e"),
            ("sample38", "0778f428-2606-4f3c-83dc-b4099b970814"),
            ("sample39", "a254f41d-125f-4d4b-b66e-564bf095b8f1"),
            ("sample40", "7807b4f5-3c98-459c-b2f9-8ad6b4f75d58"),
            ("sample41", "d6139ab1-1ad8-4cd0-9e1b-ea1ca23ca479"),
        )

        for sample_name, match_id in cases:
            self.upload_match_report_and_assert_success(sample_name, match_id)

    def upload_match_report(self, sample_name=None, sample=None, headers=None):
        if sample_name is None and sample is None:
            raise AssertionError(  # pragma: nocover
                "Both sample_name and sample are NOT given"
            )

        if sample_name is not None and sample is not None:
            raise AssertionError(  # pragma: nocover
                "sample_name and sample are BOTH given. Only one of them is required"
            )

        if headers is None:
            headers = {
                "Content-Type": "text/plain",
                "X-D0-Blind-Id-Detached-Signature": "dummy",
            }

        if sample_name is not None:
            f = open(module_path + "/match_samples/" + sample_name)
            sample = f.read()
            f.close()

        return self._test_cli.post("/stats/submit", headers=headers, data=sample)

    def upload_match_report_and_assert_success(self, sample_name: str, uuid: str):
        resp = self.upload_match_report(sample_name)
        assert resp.status_code == 200, resp.text
        resp = self._test_cli.get("/scoreboard/{0}.json".format(uuid))
        assert resp.status_code == 200, resp.json()["message"]

    def assert_scoreboard_equals_sample(self, match_id: str, sample_filename: str):
        obj_defacto = self._test_cli.get("/scoreboard/{0}.json".format(match_id)).json()
        # NOTE: if scoreboard json is changed and manually checked
        # then you can uncomment this:
        # with open(module_path + "/samples/" + sample_filename + ".json", "w") as f:
        #     f.write(json.dumps(obj_defacto, indent=4, sort_keys=True) + "\n")
        obj_expected = read_json_sample(sample_filename)
        assert obj_defacto == obj_expected

    def get(self, uri: str, expected_http_code: int = 200, **kwargs) -> Response:
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        if "if-modified-since" not in kwargs["headers"]:
            kwargs["headers"][
                "if-modified-since"
            ] = "aaaa"  # hack, to make sure that app does not get cached response
        resp = self._test_cli.get(uri, allow_redirects=False, **kwargs)
        assert resp.status_code == expected_http_code, resp.text
        return resp


@fixture(scope="session")
def test_cli():
    from qllr import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@fixture
def mock_requests_get(monkeypatch):
    def wrapped(return_value=None, side_effect=None):
        def what_to_return(*args, **kwargs):
            if side_effect:
                raise side_effect  # pragma: nocover
            return return_value

        monkeypatch.setattr("requests.get", what_to_return)

    return wrapped


@fixture(scope="session")
def service(test_cli):
    yield Service(test_cli)


@fixture
async def db(event_loop):
    from qllr.db import get_db_pool

    pool = await get_db_pool(event_loop)
    con = await pool.acquire()

    tr = con.transaction()
    await tr.start()

    yield con

    await tr.rollback()
    await pool.release(con)
