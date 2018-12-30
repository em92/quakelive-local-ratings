from .fixture import AppTestCase


class TestMatchUpload1(AppTestCase):

    def test_upload_no_signature(self):
        resp = self.upload_match_report(sample="something", headers={'Content-Type': "text/plain"})
        self.assertEqual(resp.status_code, 403)
        json = resp.get_json()
        self.assertTrue("signature" in json['message'].lower())

# TODO:
# shit posting examples
# 202 or 200

    def test_upload_junk(self):
        resp = self.upload_match_report(sample="junk sample")
        self.assertEqual(resp.status_code, 500)  # TODO: change to 422 in future

    def test_upload_sample(self):
        self.upload_match_report_and_assert_success("sample01", "69770ca5-943c-491d-931e-720c5474d33b")

    def test_upload_sample_again(self):
        resp = self.upload_match_report(sample_name="sample01")
        self.assertEqual(resp.status_code, 422)  # TODO: change to 409 in future
