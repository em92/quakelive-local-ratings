import requests
from pytest import mark, param, raises

from qllr.common import clean_name, convert_timestamp_to_tuple as cttt, request
from qllr.gametypes import GAMETYPE_RULES

gametype_rules_test_params = list(
    map(lambda x: param(x[0], x[1]), GAMETYPE_RULES.items())
)


@mark.asyncio
async def test_async_request():
    r = await request("https://httpbin.org/status/300")
    assert r.status_code == 300

    with raises(requests.exceptions.RequestException):
        await request("https://httpbin.org/delay/10")


def test_clean_name():
    assert "eugene" == clean_name("eugene")
    assert "MadGabZ" == clean_name("^1M^4ad^1G^4ab^1Z^7")
    assert "unnamed" == clean_name("")
    assert "unnamed" == clean_name("^0")


def test_convert_timestamp_to_tuple():
    assert cttt(None) == (1970, 1, 1, 0, 0, 0)
    assert cttt(1571567579) == (2019, 10, 20, 10, 32, 59)


@mark.parametrize("gametype,rules", gametype_rules_test_params)
def test_gametype_rules_calc_player_perf_type(gametype, rules):
    player_data = {
        "scoreboard-pushes": "10000",
        "scoreboard-destroyed": "4444",
        "scoreboard-score": "555",
        "scoreboard-kills": "666",
        "scoreboard-deaths": "333",
        "medal-assists": "1",
        "medal-captures": "4",
    }
    assert type(rules.calc_player_perf(player_data, 1)) is float


@mark.parametrize("gametype,rules", gametype_rules_test_params)
def test_gametype_rules_medals_in_scoreboard_mid_type(gametype, rules):
    assert type(rules.medals_in_scoreboard_mid() is list)
