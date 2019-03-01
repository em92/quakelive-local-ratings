from collections import OrderedDict
from .fixture import AppTestCase


class TestPlayer(AppTestCase):

    def setUp(self):
        cases = OrderedDict([
            ("sample04", "125f1bda-5502-4549-b5e7-4e4ab01386df"),
            ("sample05", "7d5b863f-ee71-4f74-b237-c9f743f14976"),
            ("sample06", "fddd7e05-6a1e-462c-aed1-7af81177d483"),
            ("sample07", "52b7ae54-8040-4a21-9912-9e5ee13e2caa"),
            ("sample08", "87dfda21-423e-4f6b-89f3-eefbfba1dff0"),
            ("sample09", "5185e664-e476-49ba-953d-a6d59080d50b"),
            ("sample10", "0ff2772c-e609-4368-b21f-6dffa0b898fb"),
            ("sample11", "6ba4f41b-17bd-45dc-883e-9dacb49f3092"),
            ("sample12", "93a0b31f-4326-4971-ae51-8ddd97b74b83"),
            ("sample13", "8b59128f-600f-4e34-a733-6ce82a22cd6d"),
            ("sample14", "39ac0a42-55a6-44b4-ac06-69571db6bc31"),
            ("sample15", "e3492e13-6792-4ff6-9554-ff869c7e4931"),
        ])
        for sample_name, match_id in cases.items():
            self.upload_match_report_and_assert_success(sample_name, match_id)

    def test_player_json(self):
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
        for steam_id in steam_ids:
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
