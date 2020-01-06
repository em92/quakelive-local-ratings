from pytest import mark

from qllr.blueprints.scoreboard.methods import get_medals_available

from .conftest import read_json_sample


def assert_scoreboard_html_equals_sample(
    service, match_id: str, sample_filename: str, mod_date: str
):
    resp = service.get("/scoreboard/{0}".format(match_id))
    assert resp.template.name == "scoreboard.html"
    context = resp.context
    assert "request" in context
    assert "match_id" in context
    assert context["match_id"] == match_id
    del context["request"]
    del context["match_id"]
    obj_defacto = context
    obj_expected = read_json_sample(sample_filename)
    assert obj_defacto == obj_expected
    assert resp.headers["last-modified"] == mod_date


@mark.parametrize(
    "sample_name,match_id,mod_date",
    [
        # fmt: off
        ("sample02", "44c479b9-fdbd-4674-b5bd-a56ef124e48c", "Sat, 09 Mar 2019 21:22:31 GMT"),
        ("sample03", "abdf7e7d-4e79-4f1c-9f28-6c87728ff2d4", "Sat, 09 Mar 2019 21:22:31 GMT"),
        ("sample08", "87dfda21-423e-4f6b-89f3-eefbfba1dff0", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample10", "0ff2772c-e609-4368-b21f-6dffa0b898fb", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample13", "8b59128f-600f-4e34-a733-6ce82a22cd6d", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample17", "dd961b26-bafe-4bd3-a515-c0ec156fd85c", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample20", "4b4ee658-0140-46ea-9d84-5bb802199400", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample22", "61aad138-b69d-4ae7-b02e-23a9cfb7935f", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample24", "8d599bb1-6f7f-4dcf-9e95-da62f2b1a698", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample26", "c0ac214d-b228-440b-a3fd-b5fe6ce3081d", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample28", "a22d0122-1382-4533-bf01-403114fac08f", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample31", "55ef6e6a-f7ab-4f4b-ba26-c77963147b98", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample34", "9cbb425a-b7a9-4376-9b1a-e68e8622f851", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample37", "6e34afa3-a8e0-4dba-a496-3fc17e615e8e", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample38", "0778f428-2606-4f3c-83dc-b4099b970814", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample39", "a254f41d-125f-4d4b-b66e-564bf095b8f1", "Sun, 10 Mar 2019 00:23:44 GMT"),
        ("sample40", "7807b4f5-3c98-459c-b2f9-8ad6b4f75d58", "Sun, 10 Mar 2019 00:23:44 GMT"),
        # fmt: on
    ],
)
def test_scoreboards(service, sample_name, match_id, mod_date):
    service.assert_scoreboard_equals_sample(
        match_id, "scoreboard_{}".format(sample_name, mod_date)
    )
    assert_scoreboard_html_equals_sample(
        service, match_id, "scoreboard_{}".format(sample_name), mod_date
    )


def test_not_exists_scoreboard_json(service):
    resp = service.get(
        "/scoreboard/11111111-1111-1111-1111-111111111111.json",
        404,
        headers={"accept": "text/html"},
    )
    resp.json()


def test_not_exists_scoreboard_html(service):
    resp = service.get(
        "/scoreboard/11111111-1111-1111-1111-111111111111",
        404,
        headers={"accept": "text/html"},
    )


@mark.asyncio
async def test_get_medals_available(db, service):
    assert [] == await get_medals_available(db, "00001111-2222-3333-4444-555566667777")
