from pytest import mark, param
from starlette.datastructures import Headers

from .conftest import read_json_sample

data = (
    ("76561198043212328", "Sat, 09 Mar 2019 20:30:58 GMT"),  # shire
    ("76561198257384619", "Mon, 25 Feb 2019 20:48:44 GMT"),  # HanzoHasashiSan
    ("76561197985202252", "Sat, 09 Mar 2019 20:30:58 GMT"),  # carecry
    ("76561198308265738", "Sat, 09 Mar 2019 20:06:44 GMT"),  # lookaround
    ("76561198257327401", "Sat, 09 Mar 2019 21:22:31 GMT"),  # Jalepeno
    ("76561198005116094", "Sat, 09 Mar 2019 21:22:31 GMT"),  # Xaero
    ("76561198077231066", "Sat, 29 Dec 2018 21:11:07 GMT"),  # Mike_Litoris
    ("76561198346199541", "Sat, 09 Mar 2019 20:06:44 GMT"),  # Zigurun
    ("76561198257338624", "Mon, 25 Feb 2019 20:22:26 GMT"),  # indie
    ("76561198260599288", "Sat, 29 Dec 2018 21:11:07 GMT"),  # eugene
)


@mark.parametrize("steam_id,mod_date", data)
def test_player_json(service, steam_id, mod_date):
    resp = service.get("/player/{0}.json".format(steam_id))

    obj_defacto = resp.json()
    obj_expected = read_json_sample("player_{}".format(steam_id))
    assert obj_defacto == obj_expected

    resp = service.get("/player/{0}".format(steam_id))
    assert resp.template.name == "player_stats.html"
    context = resp.context
    assert "request" in context
    assert "steam_id" in context
    assert context["steam_id"] == steam_id

    del context["request"]
    del context["steam_id"]
    obj_defacto = context
    assert obj_defacto == obj_expected

    assert resp.headers["last-modified"] == mod_date

    service.get(
        "/player/{0}.json".format(steam_id),
        304,
        headers=Headers({"If-Modified-Since": mod_date}),
    )


@mark.parametrize("steam_id,mod_date", data)
def test_deprecated_player_json(service, steam_id, mod_date):
    resp = service.get("/deprecated/player/{0}.json".format(steam_id))
    assert resp.json() == read_json_sample("deprecated_player_{0}".format(steam_id))

    assert resp.headers["last-modified"] == mod_date

    service.get(
        "/player/{0}.json".format(steam_id),
        304,
        headers=Headers({"If-Modified-Since": mod_date}),
    )
