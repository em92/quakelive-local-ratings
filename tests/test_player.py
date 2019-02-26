import json
from .fixture import AppTestCase


class TestPlayer(AppTestCase):

    def setUp(self):
        for i in range(4, 16):
            r = self.upload_match_report(sample_name="sample{:02d}".format(i))
            print(r.text)

    def test_player_json(self):
        resp = self.test_cli.get("/player/76561198166128882.json")
        print(resp.text)
