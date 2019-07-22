import requests
from pytest import mark, raises

from qllr.common import clean_name, request


@mark.asyncio
async def test_async_request():
    r = await request("https://httpbin.org/status/300")
    assert r.status_code == 300

    with raises(requests.exceptions.RequestException):
        await request("https://httpbin.org/delay/10")


def test_clean_name():
    assert "eugene" == clean_name("eugene")
    assert "MadGabZ" == clean_name("^1M^4ad^1G^4ab^1Z^7")
    assert "unnamed" == clean_name("")
    assert "unnamed" == clean_name("^0")
