from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from testcontainers.redis import RedisContainer  # type: ignore[import-untyped]

from sms_api.common.messaging.messaging_service_redis import MessagingServiceRedis
from tests.docker_utils import SKIP_DOCKER_REASON, SKIP_DOCKER_TESTS


@pytest_asyncio.fixture(scope="session")
async def redis_container_uri() -> AsyncGenerator[str, None]:
    if SKIP_DOCKER_TESTS:
        pytest.skip(SKIP_DOCKER_REASON)
    with RedisContainer() as redis_container:
        # RedisContainer uses get_connection_url() method
        connection_url = f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}"
        yield connection_url


@pytest_asyncio.fixture(scope="function")
async def redis_subscriber_service(redis_container_uri: str) -> AsyncGenerator[MessagingServiceRedis, None]:
    service = MessagingServiceRedis()
    await service.connect(redis_container_uri)
    yield service
    await service.disconnect()


@pytest_asyncio.fixture(scope="function")
async def redis_producer_service(redis_container_uri: str) -> AsyncGenerator[MessagingServiceRedis, None]:
    service = MessagingServiceRedis()
    await service.connect(redis_container_uri)
    yield service
    await service.disconnect()
