import json
from .fixture import AppTestCase


class TestScoreboard(AppTestCase):

    ORDER = 2
    maxDiff = None

    def assert_scoreboard_html_equals_sample(self, match_id: str, sample_filename: str):
        resp = self.get("/scoreboard/{0}".format(match_id))
        self.assertEqual(resp.template.name, "scoreboard.html")
        context = resp.context
        self.assertIn('request', context)
        self.assertIn('match_id', context)
        self.assertEqual(context['match_id'], match_id)
        del context['request']
        del context['match_id']
        obj_defacto = context
        obj_expected = self.read_json_sample(sample_filename)
        self.assertDictEqual(obj_defacto, obj_expected)

    def test_sample2_scoreboard_json(self):
        self.assert_scoreboard_equals_sample("44c479b9-fdbd-4674-b5bd-a56ef124e48c", "scoreboard_sample02")

    def test_sample2_scoreboard_html(self):
        self.assert_scoreboard_html_equals_sample("44c479b9-fdbd-4674-b5bd-a56ef124e48c", "scoreboard_sample02")

    def test_sample3_scoreboard_json(self):
        self.assert_scoreboard_equals_sample("abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4", "scoreboard_sample03")

    def test_sample3_scoreboard_html(self):
        self.assert_scoreboard_html_equals_sample("abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4", "scoreboard_sample03")

    def test_not_exists_scoreboard_json(self):
        resp = self.get("/scoreboard/11111111-1111-1111-1111-111111111111.json", 404, headers={'accept': 'text/html'})
        try:
            resp.json()
        except json.decoder.JSONDecodeError:
            self.fail("Expected json response")

    def test_not_exists_scoreboard_html(self):
        resp = self.get("/scoreboard/11111111-1111-1111-1111-111111111111", 404, headers={'accept': 'text/html'})
        self.assertEqual(resp.template.name, "layout.html")
