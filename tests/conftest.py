import pytest
import sys
import psycopg2
import os
from testing import postgresql as pgsql_test

postgresql = None

@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    # will execute as early as possible
    items.sort(key=lambda item: item.parent.obj.ORDER if hasattr(item.parent.obj, 'ORDER') else 0)

def pytest_configure(config):
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

    from qllr.conf import settings
    settings['use_avg_perf_tdm'] = True
    sys.path.append(sys.path[0] + "/..")


def pytest_unconfigure(config):
    global postgresql
    postgresql.stop()
