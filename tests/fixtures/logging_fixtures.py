import pytest


@pytest.fixture(scope="session", autouse=True)
def configure_logging() -> None:
    pass  # noqa: F401. to ensure logging is configured before any tests run
