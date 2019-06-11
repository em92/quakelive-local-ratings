from collections import OrderedDict

from .fixture import AppTestCase


class TestRatings(AppTestCase):
    def test_ratings_ad(self):
        resp = self.get("/ratings/ad/")
        context = resp.context

        self.assertIn("request", context)
        self.assertIn("current_page", context)
        self.assertIn("response", context)
        self.assertIn("gametype", context)

        self.assertEqual(context["gametype"], "ad")
        self.assertEqual(context["current_page"], 0)

        self.assertEqual(context["response"], self.read_json_sample("ratings_ad"))

    def test_ratings_ad_json(self):
        resp = self.get("/ratings/ad/0.json")
        self.assertEqual(resp.json()["response"], self.read_json_sample("ratings_ad"))
