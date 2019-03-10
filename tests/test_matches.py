from collections import OrderedDict
from .fixture import AppTestCase


class TestMatches(AppTestCase):

    def setUp(self):
        cases = OrderedDict([
            ("sample16", "c51c6bb7-9be2-455d-aef0-dcad07a9b4d1"),
            ("sample17", "dd961b26-bafe-4bd3-a515-c0ec156fd85c"),
            ("sample18", "77c4459a-90d0-4598-b399-971f278bdc38"),
            ("sample19", "47bf1f66-21a8-4414-a196-fb4262f2f81e"),
            ("sample20", "4b4ee658-0140-46ea-9d84-5bb802199400"),
            ("sample21", "13d71e4f-69e9-4a04-8c37-f12a35ab9d2f"),
            ("sample22", "61aad138-b69d-4ae7-b02e-23a9cfb7935f"),
            ("sample23", "44de3665-dd33-4f09-ae2e-a3f0456e6a9b"),
            ("sample24", "8d599bb1-6f7f-4dcf-9e95-da62f2b1a698"),
            ("sample25", "06b0c4d0-9720-40c5-92c5-e406c1496684"),
            ("sample26", "c0ac214d-b228-440b-a3fd-b5fe6ce3081d"),
            ("sample27", "55bce45b-305d-4ab4-8bbe-ec8ddc8bc037"),
            ("sample28", "a22d0122-1382-4533-bf01-403114fac08f"),
            ("sample29", "3bd7ffa1-2c35-48c8-8cb5-fe582c9684ba"),
            ("sample30", "a2a89cbc-3c6e-4430-b3eb-c32b610ad4ff"),
            ("sample31", "55ef6e6a-f7ab-4f4b-ba26-c77963147b98"),
            ("sample32", "0e463edf-12cf-4858-8739-83fe57e98e7a"),
            ("sample33", "3a3a88ed-f11e-404c-b362-d5ce376ec241"),
            ("sample34", "9cbb425a-b7a9-4376-9b1a-e68e8622f851"),
            ("sample35", "dd4ce899-ce86-4ec5-8b3e-c8303433a353"),
            ("sample36", "a53b8274-989d-4e07-afd8-3603d402b207"),
            ("sample37", "6e34afa3-a8e0-4dba-a496-3fc17e615e8e"),
            ("sample38", "0778f428-2606-4f3c-83dc-b4099b970814"),
            ("sample39", "a254f41d-125f-4d4b-b66e-564bf095b8f1"),
            ("sample40", "7807b4f5-3c98-459c-b2f9-8ad6b4f75d58"),
        ])
        for sample_name, match_id in cases.items():
            self.upload_match_report_and_assert_success(sample_name, match_id)

    def test_matches_all(self):
        r = self.test_cli.get("/matches/")
        print(r.text)
        r = self.test_cli.get("/matches/1")
        print(r.text)

