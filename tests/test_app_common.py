import unittest

import requests

from qllr.common import clean_name, request

from .fixture import unasync


class TestAppCommon(unittest.TestCase):
    @unasync
    async def test_async_request(self):
        r = await request("https://httpbin.org/status/300")
        self.assertEqual(r.status_code, 300)

        with self.assertRaises(requests.exceptions.RequestException):
            await request("https://httpbin.org/delay/10")

    def test_clean_name(self):
        self.assertEqual("eugene", clean_name("eugene"))
        self.assertEqual("MadGabZ", clean_name("^1M^4ad^1G^4ab^1Z^7"))
        self.assertEqual("unnamed", clean_name(""))
        self.assertEqual("unnamed", clean_name("^0"))
