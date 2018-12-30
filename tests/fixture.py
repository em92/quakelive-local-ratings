import gzip
import os
import sys
import unittest
import psycopg2

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
    test_cli = app.test_client()

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
            f = gzip.open(os.path.dirname(os.path.realpath(__file__)) + "/match_samples/" + sample_name + ".gz")
            sample = f.read()
            f.close()

        return self.test_cli.post("/stats/submit", headers=headers, data=sample)
