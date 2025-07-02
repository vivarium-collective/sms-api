import logging
import pytest
from sms_api.log_config import setup_logging

@pytest.fixture(scope="session", autouse=True)
def configure_logging() -> None:
    logger = logging.getLogger("test")
    setup_logging(logger)
