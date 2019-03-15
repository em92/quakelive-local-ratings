from collections import OrderedDict
from .fixture import AppTestCase


class TestRatings(AppTestCase):

    ORDER = 5

    def test_ratings_ad(self):
        resp = self.test_cli.get("/ratings/ad")
        self.assertEqual(
            resp.context['response'],
            self.read_json_sample("ratings_ad")
        )
