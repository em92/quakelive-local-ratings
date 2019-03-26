import unittest
from .conftest import pytest_configure
pytest_configure(None)

from .test_app_common import TestAppCommon
from .test_cache import TestCache
from .test_simple_upload import TestMatchUpload1
from .test_scoreboard import TestScoreboard
from .test_player import TestPlayer as TestZPlayer
from .test_balance_api import TestBalanceApi as TestZBalanceApi
from .test_matches import TestMatches as TestZZMatches
from .test_ratings import TestRatings as TestZZRatings
from .test_steam_api import TestSteamApi as TestZZSteamApi
from .test_export_ratings import TestExportRatings as TestZZZExportRatings


def suite():
    r = unittest.TestSuite()
    r.addTest(TestAppCommon())
    r.addTest(TestCache())
    r.addTest(TestMatchUpload1())
    r.addTest(TestScoreboard())
    r.addTest(TestZBalanceApi())
    r.addTest(TestZPlayer())
    r.addTest(TestZZMatches())
    r.addTest(TestZZRatings())
    r.addTest(TestZZSteamApi())
    r.addTest(TestZZZExportRatings())
    return r


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
