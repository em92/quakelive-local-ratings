from collections import OrderedDict
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

    def test_ratings_ad(self):
        resp = self.test_cli.get("/export_rating/ad.csv", allow_redirects=False)
        self.assertEqual(resp.status_code, 200)

        #with open(os.getcwd() + "/tests/samples/exported_ratings_ad.csv", 'w') as f:
        #    f.write(resp.text)
