from .fixture import AppTestCase


class TestAppCommon(AppTestCase):

    def test_404(self):
        resp = self.test_cli.get('/404')
        self.assertEqual(resp.status_code, 404)
