import sys
import pytest

sys.path.append(sys.path[0] + "/..")

# sys.argv[1:] = ["-c", "cfg1.json"]

from main import app  # noqa: E402


@pytest.fixture
def test_cli():
    test_client = app.test_client()
    yield test_client
