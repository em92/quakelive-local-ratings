from .fixture import AppTestCase


class TestMatches(AppTestCase):
    def test_matches_all(self):
        cases = [
            ("/matches/", 0, None, 2),
            ("/matches/1/", 1, None, 2),
            ("/matches/ad/", 0, "ad", 1),
            ("/matches/ad/1/", 1, "ad", 1),
            ("/matches/tdm/", 0, "tdm", 1),
            ("/matches/player/76561198260599288/", 0, None, 1),
        ]
        for case in cases:
            uri = case[0]
            page = case[1]
            gametype = case[2]
            page_count = case[3]
            resp = self.get(uri)
            assert resp.template.name == "match_list.html"

            context = resp.context
            assert "request" in context
            assert "current_page" in context
            assert "gametype" in context
            assert "page_count" in context
            assert context["current_page"] == page
            assert context["gametype"] == gametype
            assert context["page_count"] == page_count

            sample_filename = "match_list_{}".format(cases.index(case) + 1)
            assert context["matches"] == self.read_json_sample(sample_filename)

    def test_old_routes(self):
        pairs = [
            ("/player/123/matches", "/matches/player/123/"),
            ("/player/123/matches/", "/matches/player/123/"),
            ("/player/123/matches/456/", "/matches/player/123/456/"),
            (
                "/player/123/matches/blablabla/456/",
                "/matches/player/123/blablabla/456/",
            ),
            ("/", "/matches/"),
        ]
        for pair in pairs:
            old_uri = pair[0]
            new_uri = pair[1]
            resp = self.get(old_uri, 302)
            assert resp.headers["Location"].endswith(new_uri)
