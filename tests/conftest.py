import sys
import psycopg2
import os
from testing import postgresql as pgsql_test
from starlette.config import environ

postgresql = None


def pytest_configure(config):
    # TODO: this is dirty hack to be able to run pytest
    if config:
        return

    global postgresql

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

    # force default timezone to pass tests on os with different local timezone setting
    pgsql_test.Postgresql.DEFAULT_SETTINGS['postgres_args'] += ' -c timezone=+5'

    PGSQLFactory = pgsql_test.PostgresqlFactory(
        cache_initialized_db=True,
        on_initialized=handler
    )

    postgresql = PGSQLFactory()
    os.environ["DATABASE_URL"] = postgresql.url()

    environ['USE_AVG_PERF_TDM'] = 'TRUE'
    sys.path.append(sys.path[0] + "/..")


def pytest_unconfigure(config):
    global postgresql
    postgresql.stop()
