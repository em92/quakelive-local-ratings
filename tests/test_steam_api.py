from .conftest import read_json_sample

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


def test_players_ad_with_plus(service):
    resp = service.get(
        "/steam_api/GetPlayerSummaries/?steamids={}".format("+".join(steam_ids))
    )
    assert resp.json() == read_json_sample("steam_api_1")


def test_players_ad_with_comma(service):
    resp = service.get(
        "/steam_api/GetPlayerSummaries/?steamids={}".format(",".join(steam_ids))
    )
    assert resp.json() == read_json_sample("steam_api_1")
