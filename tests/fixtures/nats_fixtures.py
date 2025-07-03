from collections.abc import AsyncGenerator

import nats
import pytest_asyncio
from nats.aio.client import Client as NATSClient

# from nats.js import JetStreamContext
from testcontainers.nats import NatsContainer  # type: ignore[import-untyped]


@pytest_asyncio.fixture(scope="session")
async def nats_container_uri() -> AsyncGenerator[str, None]:
    with NatsContainer() as nats_container:
        yield nats_container.nats_uri()


@pytest_asyncio.fixture(scope="function")
async def nats_subscriber_client(nats_container_uri: str) -> AsyncGenerator[NATSClient, None]:
    client = await nats.connect(nats_container_uri, verbose=True)
    yield client
    await client.close()


@pytest_asyncio.fixture(scope="function")
async def nats_producer_client(nats_container_uri: str) -> AsyncGenerator[NATSClient, None]:
    client = await nats.connect(nats_container_uri, verbose=True)
    yield client
    await client.close()


# @pytest_asyncio.fixture
# async def jetstream_client(nats_container_uri: str) -> AsyncGenerator[JetStreamContext, None]:
#     nc = await nats.connect(nats_container_uri)
#     js = nc.jetstream()
#     # Create a stream for testing
#     await js.add_stream(name="TEST", subjects=["test.subject"], storage="memory")
#     yield js
#     await nc.close()
