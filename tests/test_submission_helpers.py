from qllr.db import get_db_pool
from qllr.submission import get_map_id

from .fixture import AppTestCase, unasync


class TestSubmissionHelpers(AppTestCase):
    @unasync
    async def setUp(self):
        self.pool = await get_db_pool()
        self.conn = await self.pool.acquire()

    @unasync
    async def tearDown(self):
        await self.pool.release(self.conn)

    @unasync
    async def test_get_map_id(self):
        self.assertIsInstance(await get_map_id(self.conn, "testmap1"), int)
        self.assertIsNone(await get_map_id(self.conn, "testmap2", False))
