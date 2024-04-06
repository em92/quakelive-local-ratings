from pytest import mark, param

from .conftest import read_json_sample


@mark.parametrize(
    "index,uri,page,gametype,page_count",
    [
        param(0, "/matches/", 0, None, 2),
        param(1, "/matches/1/", 1, None, 2),
        param(2, "/matches/ad/", 0, "ad", 1),
        param(3, "/matches/ad/1/", 1, "ad", 1),
        param(4, "/matches/tdm/", 0, "tdm", 1),
        param(5, "/matches/player/76561198260599288/", 0, None, 1),
        param(None, "/matches/player/76561198260599288/1/", 1, None, 1),
        param(None, "/matches/player/76561198260599288/ad/2/", 2, "ad", 1),
    ],
)
def test_matches_all(service, index, uri, page, gametype, page_count):
    resp = service.get(uri)
    assert resp.template.name == "match_list.html"

    context = resp.context
    assert "request" in context
    assert "current_page" in context
    assert "gametype" in context
    assert "page_count" in context
    assert context["current_page"] == page
    assert context["gametype"] == gametype
    assert context["page_count"] == page_count

    if index is not None:
        sample_filename = "match_list_{}".format(index + 1)
        assert context["matches"] == read_json_sample(sample_filename)


@mark.parametrize(
    "old_uri,new_uri",
    [
        param("/player/123/matches", "/matches/player/123/"),
        param("/player/123/matches/", "/matches/player/123/"),
        param("/player/123/matches/456/", "/matches/player/123/456/"),
        param(
            "/player/123/matches/blablabla/456/", "/matches/player/123/blablabla/456/"
        ),
    ],
)
def test_old_routes(service, old_uri, new_uri):
    resp = service.get(old_uri, 308)
    assert resp.headers["Location"].endswith(new_uri)


def test_root_route(service):
    resp = service.get("/", 307)
    assert resp.headers["Location"].endswith("/matches/")


@mark.parametrize(
    "time_value,match_sample",
    [
        param(1552177500, "match_list_24hour_1"),
        param(1552159110, "match_list_24hour_2"),
    ],
)
def test_matches_json24hours(service, monkeypatch, time_value, match_sample):
    from qllr.blueprints import matches

    with monkeypatch.context() as m:

        def time():
            return time_value

        m.setattr(matches, "time", time)

        resp = service.get("/matches/tdm/robot24hour.json")
        assert resp.json()["matches"] == read_json_sample(match_sample)
