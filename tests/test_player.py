from collections import OrderedDict
from .fixture import AppTestCase


class TestPlayer(AppTestCase):

    def setUp(self):
        cases = OrderedDict([
            ("sample04", "125f1bda-5502-4549-b5e7-4e4ab01386df"),
            ("sample05", "7d5b863f-ee71-4f74-b237-c9f743f14976"),
            ("sample06", "fddd7e05-6a1e-462c-aed1-7af81177d483"),
            ("sample07", "52b7ae54-8040-4a21-9912-9e5ee13e2caa"),
            ("sample08", "87dfda21-423e-4f6b-89f3-eefbfba1dff0"),
            ("sample09", "5185e664-e476-49ba-953d-a6d59080d50b"),
            ("sample10", "0ff2772c-e609-4368-b21f-6dffa0b898fb"),
            ("sample11", "6ba4f41b-17bd-45dc-883e-9dacb49f3092"),
            ("sample12", "93a0b31f-4326-4971-ae51-8ddd97b74b83"),
            ("sample13", "8b59128f-600f-4e34-a733-6ce82a22cd6d"),
            ("sample14", "39ac0a42-55a6-44b4-ac06-69571db6bc31"),
            ("sample15", "e3492e13-6792-4ff6-9554-ff869c7e4931"),
        ])
        for sample_name, match_id in cases.items():
            self.upload_match_report_and_assert_success(sample_name, match_id)

    def test_player_json(self):
        resp = self.test_cli.get("/player/76561198166128882.json")
        print(resp.text)
