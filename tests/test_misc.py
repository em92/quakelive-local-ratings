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
