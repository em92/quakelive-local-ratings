from .conftest import read_json_sample, read_sample


def test_ratings_ad_redirect(service):
    resp = service.get("/export_rating/csv/ad", 308)

    new_url = resp.headers["Location"]
    assert new_url.endswith("/export_rating/ad.csv")


def test_ratings_ad_redirect_json(service):
    resp = service.get("/export_rating/json/ad", 308)

    new_url = resp.headers["Location"]
    assert new_url.endswith("/export_rating/ad.json")


def test_ratings_ad_redirect_bad_format(service):
    service.get("/export_rating/blablabla/ad", 404)


def test_ratings_ad_csv(service):
    resp = service.get("/export_rating/ad.csv")
    assert resp.encoding == "utf-8"
    assert resp.text == read_sample("exported_ratings_ad.csv")


def test_ratings_ad_json(service):
    resp = service.get("/export_rating/ad.json")
    assert resp.json() == read_json_sample("exported_ratings_ad")
