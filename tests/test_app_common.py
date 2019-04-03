from .fixture import AppTestCase


class TestAppCommon(AppTestCase):
    def test_404(self):
        self.get("/404", 404)
