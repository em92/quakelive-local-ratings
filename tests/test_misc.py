from qllr.db import SurjectionDict


def test_root_route(service):
    resp = service.get("/", 307)
    assert resp.headers["Location"].endswith("/matches/")


def test_root_about_redirect(service):
    resp = service.get("/about/", 307)
    assert resp.headers["Location"].endswith("/about")


def test_root_about(service):
    service.get("/about", 200)


def test_robots_txt(service):
    resp = service.get("/robots.txt", 200)
    assert "Allow:" not in resp.text


def test_surjection_dict():
    surjection = {
        1: "ad",
        2: "ctf",
    }
    d = SurjectionDict(surjection)
    d[1] = "v1"
    d["ctf"] = "v2"
    assert d["ad"] == "v1"
    assert d[2] == "v2"
    assert len(d) == 2
    assert repr(d) == repr({"ad": "v1", "ctf": "v2"})

    del d["ctf"]
    assert len(d) == 1
    assert d.get("ctf") is None
    assert d.get("ad") == "v1"

    del d[1]
    assert len(d) == 0
    assert d.get("ctf") is None
    assert d.get("ad") is None


def test_favicon(service):
    service.get("/static/images/favicon.png", 200)

    resp = service.get("/favicon.ico", 307)
    assert resp.headers["Location"].endswith("/static/images/favicon.png")
