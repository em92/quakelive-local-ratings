from .fixture import AppTestCase


class TestBalanceApi(AppTestCase):

    ORDER = 2
    maxDiff = None

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

    def steam_ids_as_string_with_plus(self):
        return "+".join(self.steam_ids)

    def assert_balance_api_data_equal(self, first: dict, second: dict):
        self.assertIn("playerinfo", first)
        self.assertIn("playerinfo", second)
        self.assertDictEqual(first["playerinfo"], second["playerinfo"])

        self.assertIn("players", first)
        self.assertIn("players", second)
        self.assert_lists_have_same_elements(first["players"], second["players"])

        self.assertIn("deactivated", first)
        self.assertIn("deactivated", second)
        self.assert_lists_have_same_elements(
            first["deactivated"], second["deactivated"]
        )

        self.assertIn("untracked", first)
        self.assertIn("untracked", second)
        self.assert_lists_have_same_elements(first["untracked"], second["untracked"])

    def test_simple_ad_only_players(self):
        self.assert_balance_api_data_equal(
            self.get("/elo/" + self.steam_ids_as_string_with_plus()).json(),
            self.read_json_sample("balance_api_ad_only_players"),
        )

    def test_map_based1(self):
        # TODO: тесты проваливаются, т.к. переписали
        # TODO: написать тесты, где используется среднее арифметическое
        self.assert_balance_api_data_equal(
            self.get(
                "/elo/map_based/ad/japanesecastles/"
                + self.steam_ids_as_string_with_plus()
            ).json(),

            self.read_json_sample("balance_api_ad_japanesecastles"),
        )
        # TODO: add gametype check

    def test_map_based2(self):
        response = self.get(
            "/elo/" + "+".join(self.steam_ids),
            302,
            headers={
                "X-QuakeLive-Gametype": "ad",
                "X-QuakeLive-Map": "japanesecastles",
            },
        )

        new_url = response.headers["Location"]
        self.assertTrue(
            new_url.endswith(
                "/elo/map_based/ad/japanesecastles/"
                + self.steam_ids_as_string_with_plus()
            )
        )
        # TODO: add gametype check
