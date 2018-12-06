import gzip
import os
import sys
import unittest
from conf import settings

settings['db_url'] = "postgres://eugene:bebebe@db:5432/qllr"
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
