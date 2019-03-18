from .fixture import AppTestCase


class TestExportRatings(AppTestCase):

    ORDER = 5

    def test_ratings_ad_redirect(self):
        resp = self.test_cli.get("/export_rating/csv/ad", allow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        new_url = resp.headers["Location"]
        self.assertTrue(
            new_url.endswith("/export_rating/ad.csv")
        )

    def test_ratings_ad_csv(self):
        resp = self.test_cli.get("/export_rating/ad.csv", allow_redirects=False)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.text, self.read_sample("exported_ratings_ad.csv"))

    def test_ratings_ad_json(self):
        resp = self.test_cli.get("/export_rating/ad.json", allow_redirects=False)
        self.assertEqual(resp.status_code, 200)
        self.assertDictEqual(
            resp.json(),
            self.read_json_sample("exported_ratings_ad")
        )


