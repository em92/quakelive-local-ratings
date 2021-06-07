def test_root_route(service):
    resp = service.get("/", 307)
    assert resp.headers["Location"].endswith("/matches/")


def test_robots_txt(service):
    resp = service.get("/robots.txt", 200)
    assert "Allow:" not in resp.text
