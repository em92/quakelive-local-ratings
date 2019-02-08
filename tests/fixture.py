import gzip
import json
import os
import sys
import typing
import unittest
import psycopg2

from starlette.testclient import TestClient

from testing import postgresql as pgsql_test
from conf import settings

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


PGSQLFactory = pgsql_test.PostgresqlFactory(
    cache_initialized_db=True,
    on_initialized=handler
)

postgresql = PGSQLFactory()
os.environ["DATABASE_URL"] = postgresql.url()

sys.path.append(sys.path[0] + "/..")
from main import app  # noqa: E402


class AppTestCase(unittest.TestCase):
    test_cli = TestClient(app)
    module_path = os.path.dirname(os.path.realpath(__file__))

    def upload_match_report(self, sample_name=None, sample=None, headers=None):
        if sample_name is None and sample is None:
            raise AssertionError("Both sample_name and sample are NOT given")

        if sample_name is not None and sample is not None:
            raise AssertionError("sample_name and sample are BOTH given. Only one of them is required")

        if headers is None:
            headers = {
                'Content-Type': "text/plain",
                'X-D0-Blind-Id-Detached-Signature': "dummy",
            }

        if sample_name is not None:
            f = gzip.open(self.module_path + "/match_samples/" + sample_name + ".gz")
            sample = f.read()
            f.close()

        return self.test_cli.post("/stats/submit", headers=headers, data=sample)

    def upload_match_report_and_assert_success(self, sample_name: str, uuid: str):
        resp = self.upload_match_report(sample_name)
        self.assertEqual(resp.status_code, 200)
        resp = self.test_cli.get(f"/scoreboard/{uuid}.json")
        json = resp.get_json()
        self.assertEqual(json['ok'], True)

    def read_json_sample(self, sample_filename: str) -> typing.Dict:
        with gzip.open(self.module_path + "/samples/" + sample_filename + ".json.gz") as f:
            result = f.read()
        return json.loads(result)

    def read_scoreboard(self, filename: str) -> typing.Dict:
        with gzip.open(self.module_path + "/match_samples/" + filename + ".gz") as f:
            result = f.read()
        return json.loads(result)

    def assert_scoreboard_equals_sample(self, match_id: str, sample_filename: str):
        obj_defacto = self.test_cli.get(f"/scoreboard/{match_id}.json").get_json()
        obj_expected = self.read_scoreboard(sample_filename)
        self.assertDictEqual(obj_defacto, obj_expected)
