import json

from .fixture import AppTestCase


class TestScoreboard(AppTestCase):
    def assert_scoreboard_html_equals_sample(self, match_id: str, sample_filename: str):
        resp = self.get("/scoreboard/{0}".format(match_id))
        assert resp.template.name == "scoreboard.html"
        context = resp.context
        assert "request" in context
        assert "match_id" in context
        assert context["match_id"] == match_id
        del context["request"]
        del context["match_id"]
        obj_defacto = context
        obj_expected = self.read_json_sample(sample_filename)
        assert obj_defacto == obj_expected

    def test_scoreboards(self):
        cases = [
            ("sample02", "44c479b9-fdbd-4674-b5bd-a56ef124e48c"),
            ("sample03", "abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4"),
            ("sample08", "87dfda21-423e-4f6b-89f3-eefbfba1dff0"),
            ("sample10", "0ff2772c-e609-4368-b21f-6dffa0b898fb"),
            ("sample13", "8b59128f-600f-4e34-a733-6ce82a22cd6d"),
            ("sample17", "dd961b26-bafe-4bd3-a515-c0ec156fd85c"),
            ("sample20", "4b4ee658-0140-46ea-9d84-5bb802199400"),
            ("sample22", "61aad138-b69d-4ae7-b02e-23a9cfb7935f"),
            ("sample24", "8d599bb1-6f7f-4dcf-9e95-da62f2b1a698"),
            ("sample26", "c0ac214d-b228-440b-a3fd-b5fe6ce3081d"),
            ("sample28", "a22d0122-1382-4533-bf01-403114fac08f"),
            ("sample31", "55ef6e6a-f7ab-4f4b-ba26-c77963147b98"),
            ("sample34", "9cbb425a-b7a9-4376-9b1a-e68e8622f851"),
            ("sample37", "6e34afa3-a8e0-4dba-a496-3fc17e615e8e"),
            ("sample38", "0778f428-2606-4f3c-83dc-b4099b970814"),
            ("sample39", "a254f41d-125f-4d4b-b66e-564bf095b8f1"),
            ("sample40", "7807b4f5-3c98-459c-b2f9-8ad6b4f75d58"),
        ]
        for sample_name, match_id in cases:
            try:
                self.assert_scoreboard_equals_sample(
                    match_id, "scoreboard_{}".format(sample_name)
                )
                self.assert_scoreboard_html_equals_sample(
                    match_id, "scoreboard_{}".format(sample_name)
                )
            except AssertionError as e:
                raise AssertionError("{}: {}".format(sample_name, e))

    def test_not_exists_scoreboard_json(self):
        resp = self.get(
            "/scoreboard/11111111-1111-1111-1111-111111111111.json",
            404,
            headers={"accept": "text/html"},
        )
        try:
            resp.json()
        except json.decoder.JSONDecodeError:
            self.fail("Expected json response")

    def test_not_exists_scoreboard_html(self):
        resp = self.get(
            "/scoreboard/11111111-1111-1111-1111-111111111111",
            404,
            headers={"accept": "text/html"},
        )
        assert resp.template.name == "layout.html"
