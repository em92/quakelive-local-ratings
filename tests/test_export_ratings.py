from .fixture import AppTestCase


class TestExportRatings(AppTestCase):

    ORDER = 5

    def test_ratings_ad_redirect(self):
        resp = self.get("/export_rating/csv/ad", 302)

        new_url = resp.headers["Location"]
        self.assertTrue(new_url.endswith("/export_rating/ad.csv"))

    def test_ratings_ad_csv(self):
        resp = self.get("/export_rating/ad.csv")
        self.assertEqual(resp.text, self.read_sample("exported_ratings_ad.csv"))

    def test_ratings_ad_json(self):
        resp = self.get("/export_rating/ad.json")
        self.assertDictEqual(resp.json(), self.read_json_sample("exported_ratings_ad"))
