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
        # TODO: написать тесты, где используется среднее арифметическое
        # TODO: слишком маленькая выборка. Результаты почти не отличаются от test_simple_ad_only_players
        self.assert_balance_api_data_equal(
            self.get(
                "/elo/map_based/ad/dividedcrossings/"
                + self.steam_ids_as_string_with_plus()
                + "+76561198257183089"  # played dividedcrossings at least 2 times
            ).json(),

            self.read_json_sample("balance_api_ad_dividedcrossings"),
        )
        # TODO: add gametype check

    def test_map_based_map_not_exists(self):
        def set_games_zero(data: dict):
            for key, value in data.items():
                if isinstance(value, list):
                    data[key] = [set_games_zero(x) for x in value]
                elif isinstance(value, dict):
                    data[key] = set_games_zero(value)
                elif key == "games":
                    data[key] = 0

            return data

        ratings_data = self.get("/elo/map_based/ad/this_map_does_not_exist/" + self.steam_ids_as_string_with_plus()).json()

        self.assert_balance_api_data_equal(
            ratings_data,
            set_games_zero(self.read_json_sample("balance_api_ad_only_players")),
        )

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
