import pytest

@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    # will execute as early as possible
    items.sort(key=lambda item: item.parent.obj.ORDER if hasattr(item.parent.obj, 'ORDER') else 0)
