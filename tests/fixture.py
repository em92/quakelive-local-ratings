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
settings['db_url'] = postgresql.url()

sys.path.append(sys.path[0] + "/..")
from main import app  # noqa: E402


class AppTestCase(unittest.TestCase):
    test_cli = app.test_client()
