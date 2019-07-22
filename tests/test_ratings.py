from .conftest import read_json_sample


def test_ratings_ad(service):
    resp = service.get("/ratings/ad/")
    context = resp.context

    assert "request" in context
    assert "current_page" in context
    assert "response" in context
    assert "gametype" in context

    assert context["gametype"] == "ad"
    assert context["current_page"] == 0

    assert context["response"] == read_json_sample("ratings_ad")


def test_ratings_ad_json(service):
    resp = service.get("/ratings/ad/0.json")
    assert resp.json()["response"] == read_json_sample("ratings_ad")
