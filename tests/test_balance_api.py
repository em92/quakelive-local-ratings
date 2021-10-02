from json import dumps

import requests
from pytest import mark, param

from qllr.blueprints.balance_api.methods import fetch

from .conftest import Service, read_json_sample

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
            raise ValueError("bad json")  # pragma: nocover
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


def stringify_dicts_in_list(l):
    return list(map(lambda item: dumps(item, sort_keys=True, indent=2), l))


def assert_balance_api_data_equal(first: dict, second: dict):
    assert "playerinfo" in first
    assert "playerinfo" in second
    assert set(first["playerinfo"]) == set(second["playerinfo"])

    assert "players" in first
    assert "players" in second
    assert set(stringify_dicts_in_list(first["players"])) == set(
        stringify_dicts_in_list(second["players"])
    )

    assert "deactivated" in first
    assert "deactivated" in second
    assert set(first["deactivated"]) == set(second["deactivated"])

    assert "untracked" in first
    assert "untracked" in second
    assert set(first["untracked"]) == set(second["untracked"])


def default_ratings(steamid):
    return {
        "untracked": [],
        "players": [
            {
                "ad": {"elo": 25.0, "games": 0},
                "ca": {"elo": 25.0, "games": 0},
                "ctf": {"elo": 25.0, "games": 0},
                "ft": {"elo": 25.0, "games": 0},
                "steamid": steamid,
                "tdm": {"elo": 25.0, "games": 0},
                "tdm2v2": {"elo": 25.0, "games": 0},
            }
        ],
        "playerinfo": {
            steamid: {
                "allowRating": True,
                "deactivated": False,
                "privacy": "public",
                "ratings": {
                    "ad": {"elo": 25.0, "games": 0},
                    "ca": {"elo": 25.0, "games": 0},
                    "ctf": {"elo": 25.0, "games": 0},
                    "ft": {"elo": 25.0, "games": 0},
                    "steamid": steamid,
                    "tdm": {"elo": 25.0, "games": 0},
                    "tdm2v2": {"elo": 25.0, "games": 0},
                },
            }
        },
        "deactivated": [],
    }


def test_bigger_numbers(service: Service):
    response = service.get("/elo/bn/" + STEAM_IDS_AD_PLAYERS, 200)
    assert_balance_api_data_equal(
        response.json(), read_json_sample("balance_api_ad_bigger_numbers")
    )


def test_simple_ad_only_players(service: Service):
    assert_balance_api_data_equal(
        service.get("/elo/" + STEAM_IDS_AD_PLAYERS).json(),
        read_json_sample("balance_api_ad_only_players"),
    )


def test_simple_tdm_only_players(service):
    assert_balance_api_data_equal(
        service.get("/elo/" + STEAM_IDS_TDM_PLAYERS).json(),
        read_json_sample("balance_api_tdm_only_players"),
    )


def test_not_existing_player(service: Service):
    assert_balance_api_data_equal(
        service.get("/elo/100500").json(),
        default_ratings("100500"),
    )


def test_map_based_tdm(service):
    response = service.get(
        "/elo/map_based/" + STEAM_IDS_TDM_PLAYERS + "+76561198125710191",
        200,
        headers={"X-QuakeLive-Map": "hiddenfortress"},
    )

    assert_balance_api_data_equal(
        response.json(), read_json_sample("balance_api_tdm_hiddenfortress")
    )


def test_map_based_ad(service):
    response = service.get(
        "/elo/map_based/"
        + STEAM_IDS_AD_PLAYERS
        + "+76561198257183089",  # played dividedcrossings at least 2 times
        200,
        headers={"X-QuakeLive-Map": "dividedcrossings"},
    )

    assert_balance_api_data_equal(
        response.json(), read_json_sample("balance_api_ad_dividedcrossings")
    )


def test_map_based_map_not_exists(service: Service):
    def set_games_zero(data: dict):
        for key, value in data.items():
            if isinstance(value, list):
                data[key] = [set_games_zero(x) for x in value]
            elif isinstance(value, dict):
                data[key] = set_games_zero(value)
            elif key == "games":
                data[key] = 0

        return data

    response = service.get(
        "/elo/map_based/" + STEAM_IDS_AD_PLAYERS,
        200,
        headers={"X-QuakeLive-Map": "this_map_does_not_exist"},
    )

    ratings_data = response.json()

    assert_balance_api_data_equal(
        ratings_data, set_games_zero(read_json_sample("balance_api_ad_only_players"))
    )


def test_with_qlstats_policy(service: Service, mock_requests_get):
    mock_requests_get(FakeQLStatsResponse())
    response = service.get(
        "/elo/with_qlstats_policy/76561198260599288+76561198043212328"
    )

    assert_balance_api_data_equal(
        response.json(), read_json_sample("balance_api_with_qlstats_policy")
    )


@mark.parametrize(
    "return_value,side_effect",
    [
        param(
            FakeQLStatsResponse(),
            requests.exceptions.RequestException("something bad happened"),
        ),
        param(FakeQLStatsResponse(False), None),
        param(FakeQLStatsResponse(True, True), None),
    ],
)
def test_with_qlstats_policy_with_error(
    service: Service, mock_requests_get, return_value, side_effect
):
    mock_requests_get(return_value, side_effect)
    response = service.get(
        "/elo/with_qlstats_policy/76561198260599288+76561198043212328"
    )

    assert_balance_api_data_equal(
        response.json(), read_json_sample("balance_api_with_qlstats_policy_fallback")
    )


@mark.parametrize("mapname", [None, "shiningforces"])
@mark.asyncio
async def test_nulled_ratings(db, mapname):
    """
    Make sure, that rows with null ratings are handled correctly
    """
    await db.execute(
        "INSERT INTO players(steam_id, name, model, last_played_timestamp) VALUES (76561198051160294, 'h.dogan', 'visor/default', 1543095331)"
    )
    await db.execute(
        "INSERT INTO gametype_ratings(steam_id, gametype_id, n, last_played_timestamp) VALUES (76561198051160294, 1, 0, 1477510451)"
    )
    assert await fetch(db, [76561198051160294], mapname) == default_ratings(
        "76561198051160294"
    )
