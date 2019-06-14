from unittest.mock import patch

import requests

from .fixture import AppTestCase

STEAM_IDS_TDM_PLAYERS = "+".join(
    [
        "76561198273556024",  # trig
        "76561198256352933",  # om3n
        "76561198256203867",  # prestij
        "76561198257561075",  # antonio_by
    ]
)

STEAM_IDS_AD_PLAYERS = "+".join(
    [
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
)


class FakeQLStatsResponse:
    def __init__(self, ok: bool = True, bad_json: bool = False):
        self.ok = ok
        self.bad_json = bad_json

    def json(self):
        if self.bad_json:
            raise ValueError("bad json")
        return {
            "untracked": [],
            "players": [
                {
                    "steamid": "76561198043212328",
                    "ft": {"games": 0, "elo": 900},
                    "ad": {"games": 1, "elo": 1788},
                    "tdm": {"games": 0, "elo": 900},
                    "ca": {"games": 97, "elo": 1255},
                    "ctf": {"games": 20, "elo": 1865},
                    "ffa": {"games": 4, "elo": 1791},
                },
                {
                    "steamid": "76561198260599288",
                    "duel": {"games": 32, "elo": 1386},
                    "ft": {"games": 96, "elo": 1594},
                    "ad": {"games": 5, "elo": 1648},
                    "tdm": {"games": 4, "elo": 1146},
                    "ca": {"games": 1297, "elo": 1373},
                    "ctf": {"games": 58, "elo": 1406},
                    "ffa": {"games": 342, "elo": 1938},
                },
            ],
            "playerinfo": {
                "76561198043212328": {
                    "deactivated": False,
                    "ratings": {
                        "ctf": {"games": 20, "elo": 1865},
                        "ca": {"games": 97, "elo": 1255},
                        "ft": {"games": 0, "elo": 900},
                        "tdm": {"games": 0, "elo": 900},
                        "ffa": {"games": 4, "elo": 1791},
                    },
                    "allowRating": True,
                    "privacy": "anonymous",
                },
                "76561198260599288": {
                    "deactivated": False,
                    "ratings": {
                        "ctf": {"games": 58, "elo": 1406},
                        "ca": {"games": 1297, "elo": 1373},
                        "ft": {"games": 96, "elo": 1594},
                        "tdm": {"games": 4, "elo": 1146},
                        "ffa": {"games": 342, "elo": 1938},
                    },
                    "allowRating": True,
                    "privacy": "what?",
                },
            },
            "deactivated": [],
        }


class TestBalanceApi(AppTestCase):

    maxDiff = None

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

    def test_bigger_numbers(self):
        response = self.get("/elo/bn/" + STEAM_IDS_AD_PLAYERS, 200)
        self.assert_balance_api_data_equal(
            response.json(), self.read_json_sample("balance_api_ad_bigger_numbers")
        )

    def test_simple_ad_only_players(self):
        self.assert_balance_api_data_equal(
            self.get("/elo/" + STEAM_IDS_AD_PLAYERS).json(),
            self.read_json_sample("balance_api_ad_only_players"),
        )

    def test_simple_tdm_only_players(self):
        self.assert_balance_api_data_equal(
            self.get("/elo/" + STEAM_IDS_TDM_PLAYERS).json(),
            self.read_json_sample("balance_api_tdm_only_players"),
        )

    def test_map_based_tdm(self):
        response = self.get(
            "/elo/map_based/" + STEAM_IDS_TDM_PLAYERS + "+76561198125710191",
            200,
            headers={"X-QuakeLive-Map": "hiddenfortress"},
        )

        self.assert_balance_api_data_equal(
            response.json(), self.read_json_sample("balance_api_tdm_hiddenfortress")
        )

    def test_map_based_ad(self):
        response = self.get(
            "/elo/map_based/"
            + STEAM_IDS_AD_PLAYERS
            + "+76561198257183089",  # played dividedcrossings at least 2 times
            200,
            headers={"X-QuakeLive-Map": "dividedcrossings"},
        )

        self.assert_balance_api_data_equal(
            response.json(), self.read_json_sample("balance_api_ad_dividedcrossings")
        )

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

        response = self.get(
            "/elo/map_based/" + STEAM_IDS_AD_PLAYERS,
            200,
            headers={"X-QuakeLive-Map": "this_map_does_not_exist"},
        )

        ratings_data = response.json()

        self.assert_balance_api_data_equal(
            ratings_data,
            set_games_zero(self.read_json_sample("balance_api_ad_only_players")),
        )

    @patch("requests.get", return_value=FakeQLStatsResponse())
    def test_with_qlstats_policy(self, mock):
        response = self.get(
            "/elo/with_qlstats_policy/76561198260599288+76561198043212328"
        )

        self.assert_balance_api_data_equal(
            response.json(), self.read_json_sample("balance_api_with_qlstats_policy")
        )

    def _test_with_qlstats_policy_with_error(self, mock):
        response = self.get(
            "/elo/with_qlstats_policy/76561198260599288+76561198043212328"
        )

        self.assert_balance_api_data_equal(
            response.json(),
            self.read_json_sample("balance_api_with_qlstats_policy_fallback"),
        )

    test_with_qlstats_policy_request_exception = patch(
        "requests.get",
        return_value=FakeQLStatsResponse(),
        side_effect=requests.exceptions.RequestException("something bad happened"),
    )(_test_with_qlstats_policy_with_error)

    test_with_qlstats_policy_request_exception_not_ok = patch(
        "requests.get", return_value=FakeQLStatsResponse(False)
    )(_test_with_qlstats_policy_with_error)

    test_with_qlstats_policy_request_exception_bad_json = patch(
        "requests.get", return_value=FakeQLStatsResponse(True, True)
    )(_test_with_qlstats_policy_with_error)
