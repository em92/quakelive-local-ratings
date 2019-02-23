from .fixture import AppTestCase


class TestScoreboard(AppTestCase):

    def test_sample2_scoreboard(self):
        # TODO: make sure, sample2 is uploaded
        self.assert_scoreboard_equals_sample("44c479b9-fdbd-4674-b5bd-a56ef124e48c", "scoreboard_after_sample02.json")

    def test_sample3_scoreboard(self):
        # TODO: make sure, sample3 is uploaded
        self.assert_scoreboard_equals_sample("abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4", "scoreboard_after_sample03.json")

    def test_not_exists_scoreboard(self):
        resp = self.test_cli.get("/scoreboard/11111111-1111-1111-1111-111111111111.json")
        self.assertEqual(resp.status_code, 404)
