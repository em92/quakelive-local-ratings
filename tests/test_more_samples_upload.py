from .fixture import AppTestCase


class TestMatchUpload2(AppTestCase):

    def test_upload_sample2(self):
        # TODO: make sure, sample01 is uploaded
        self.upload_match_report_and_assert_success("sample02", "44c479b9-fdbd-4674-b5bd-a56ef124e48c")

    def test_upload_sample3(self):
        # TODO: make sure, sample02 is uploaded
        self.upload_match_report_and_assert_success("sample03", "abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4")
