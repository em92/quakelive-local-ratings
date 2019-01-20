import unittest

from .test_app_common import TestAppCommon
from .test_cache import TestCache
from .test_simple_upload import TestMatchUpload1
from .test_more_samples_upload import TestMatchUpload2


def suite():
    r = unittest.TestSuite()
    r.addTest(TestAppCommon())
    r.addTest(TestCache())
    r.addTest(TestMatchUpload1())
    r.addTest(TestMatchUpload2())
    return r


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
