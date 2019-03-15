from collections import OrderedDict
from .fixture import AppTestCase


class TestMatchUpload1(AppTestCase):

    ORDER = 1

    def test_upload_no_signature(self):
        resp = self.upload_match_report(sample="something", headers={'Content-Type': "text/plain"})
        self.assertEqual(resp.status_code, 403)
        json = resp.json()
        self.assertTrue("signature" in json['message'].lower())

# TODO:
# shit posting examples
# 202 or 200

    def test_upload_junk(self):
        resp = self.upload_match_report(sample="junk sample")
        self.assertEqual(resp.status_code, 500)  # TODO: change to 422 in future

    def test_upload_sample(self):
        cases = OrderedDict([
            ("sample01", "69770ca5-943c-491d-931e-720c5474d33b"),
            ("sample02", "44c479b9-fdbd-4674-b5bd-a56ef124e48c"),
            ("sample03", "abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4"),
        ])
        for sample_name, match_id in cases.items():
            self.upload_match_report_and_assert_success(sample_name, match_id)

    def test_upload_sample_again(self):
        resp = self.upload_match_report(sample_name="sample01")
        self.assertEqual(resp.status_code, 409)
