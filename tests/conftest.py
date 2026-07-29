import pytest


@pytest.fixture(scope="session", autouse=True)
def never_sleep():
    """Make `time.sleep()` calls no-ops."""

    session_patcher = pytest.MonkeyPatch()
    with session_patcher.context() as patcher:
        patcher.setattr("time.sleep", lambda _: None)
        yield
