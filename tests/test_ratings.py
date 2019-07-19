from collections import OrderedDict

from .fixture import AppTestCase


class TestRatings(AppTestCase):
    def test_ratings_ad(self):
        resp = self.get("/ratings/ad/")
        context = resp.context

        assert "request" in context
        assert "current_page" in context
        assert "response" in context
        assert "gametype" in context

        assert context["gametype"] == "ad"
        assert context["current_page"] == 0

        assert context["response"] == self.read_json_sample("ratings_ad")

    def test_ratings_ad_json(self):
        resp = self.get("/ratings/ad/0.json")
        assert resp.json()["response"] == self.read_json_sample("ratings_ad")
