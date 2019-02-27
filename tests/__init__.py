import unittest

from .test_app_common import TestAppCommon
from .test_cache import TestCache
from .test_simple_upload import TestMatchUpload1
from .test_scoreboard import TestScoreboard
from .test_player import TestPlayer as TestZPlayer
from .test_balance_api import TestBalanceApi as TestZBalanceApi


def suite():
    r = unittest.TestSuite()
    r.addTest(TestAppCommon())
    r.addTest(TestCache())
    r.addTest(TestMatchUpload1())
    r.addTest(TestScoreboard())
    r.addTest(TestZBalanceApi())
    r.addTest(TestZPlayer())
    return r


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
