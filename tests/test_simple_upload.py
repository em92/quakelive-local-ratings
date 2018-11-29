from .fixture import AppTestCase


class TestSimpleUpload(AppTestCase):

    def test_upload_no_signature(self):
        resp = self.upload_match_report(sample="something", headers={'Content-Type': "text/plain"})
        self.assertEqual(resp.status_code, 403)
        json = resp.get_json()
        self.assertTrue("signature" in json['message'].lower())

# TODO:
# match already exists
# shit posting examples
# 202 or 200

# TODO in next major release:
# no 500 errors
    def test_upload_junk(self):
        resp = self.upload_match_report(sample="junk sample")
        self.assertEqual(resp.status_code, 500)

    def test_upload_sample(self):
        resp = self.upload_match_report(sample_name="sample01")
        self.assertEqual(resp.status_code, 200)
