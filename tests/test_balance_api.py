from .fixture import AppTestCase


class TestBalanceApi(AppTestCase):
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
    ]

    def test_simple_ad_only_players(self):
        self.assertDictEqual(
            self.test_cli.get("/elo/" + "+".join(self.steam_ids)).get_json(),
            self.read_json_sample("balance_api_ad_only_players")
        )


    def test_map_based(self):
        pass  # TODO: implement this
