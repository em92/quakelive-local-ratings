from .fixture import AppTestCase


class TestPlayer(AppTestCase):

    maxDiff = None
    ORDER = 3
    steam_ids = [
        "76561198043212328",  # shire
        "76561198257384619",  # HanzoHasashiSan
        "76561197985202252",  # carecry
        "76561198308265738",  # lookaround
        "76561198257327401",  # Jalepeno
        "76561198005116094",  # Xaero
        "76561198077231066",  # Mike_Litoris
        "76561198346199541",  # Zigurun
        "76561198257338624",  # indie
        "76561198260599288",  # eugene
    ]

    def test_player_json(self):
        for steam_id in self.steam_ids:
            resp = self.test_cli.get("/player/{0}.json".format(steam_id))
            self.assertEqual(resp.status_code, 200)

            obj_defacto = resp.json()
            obj_expected = self.read_json_sample("player_{}".format(steam_id))
            self.assertDictEqual(obj_defacto, obj_expected)

            resp = self.test_cli.get("/player/{0}".format(steam_id))
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.template.name, "player_stats.html")
            context = resp.context
            self.assertIn('request', context)
            self.assertIn('steam_id', context)
            self.assertEqual(context['steam_id'], steam_id)

            del context['request']
            del context['steam_id']
            obj_defacto = context
            self.assertDictEqual(obj_defacto, obj_expected)

    def test_deprecated_player_json(self):
        for steam_id in self.steam_ids:
            resp = self.test_cli.get("/deprecated/player/{0}.json".format(steam_id))
            self.assertDictEqual(
                resp.json(),
                self.read_json_sample("deprecated_player_{0}".format(steam_id))
            )
