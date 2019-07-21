from pytest import mark

from qllr.submission import get_map_id


@mark.asyncio
async def test_get_map_id(db):
    assert isinstance(await get_map_id(db, "testmap1"), int)
    assert await get_map_id(db, "testmap2", False) is None
