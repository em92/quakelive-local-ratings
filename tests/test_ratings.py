from pytest import mark, param

from .conftest import read_json_sample


@mark.parametrize(
    "query_string,expected_show_inactive",
    [param("", False), param("show_inactive=yes", True)],
)
def test_ratings_ad(service, query_string: str, expected_show_inactive: bool):
    uri = "/ratings/ad/"
    uri += "?" + query_string if query_string else ""
    resp = service.get(uri)
    context = resp.context

    assert "request" in context
    assert "current_page" in context
    assert "response" in context
    assert "gametype" in context

    assert context["gametype"] == "ad"
    assert context["current_page"] == 0
    assert context["show_inactive"] == expected_show_inactive

    assert context["response"] == read_json_sample("ratings_ad")


def test_ratings_ad_json(service):
    resp = service.get("/ratings/ad/0.json")
    assert resp.json()["response"] == read_json_sample("ratings_ad")
