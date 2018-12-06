import unittest

from .test_app_common import TestAppCommon
from .test_cache import TestCache
from .test_simple_upload import TestSimpleUpload


def suite():
    r = unittest.TestSuite()
    r.addTest(TestAppCommon())
    r.addTest(TestCache())
    r.addTest(TestSimpleUpload())
    return r


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())
