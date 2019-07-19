from .fixture import AppTestCase


class TestExportRatings(AppTestCase):
    def test_ratings_ad_redirect(self):
        resp = self.get("/export_rating/csv/ad", 302)

        new_url = resp.headers["Location"]
        assert new_url.endswith("/export_rating/ad.csv")

    def test_ratings_ad_redirect_json(self):
        resp = self.get("/export_rating/json/ad", 302)

        new_url = resp.headers["Location"]
        assert new_url.endswith("/export_rating/ad.json")

    def test_ratings_ad_redirect_bad_format(self):
        self.get("/export_rating/blablabla/ad", 404)

    def test_ratings_ad_csv(self):
        resp = self.get("/export_rating/ad.csv")
        assert resp.text == self.read_sample("exported_ratings_ad.csv")

    def test_ratings_ad_json(self):
        resp = self.get("/export_rating/ad.json")
        assert resp.json() == self.read_json_sample("exported_ratings_ad")
