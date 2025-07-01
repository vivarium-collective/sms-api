from collections.abc import AsyncGenerator

import nats
import pytest_asyncio
from nats.aio.client import Client as NATSClient
from testcontainers.nats import NatsContainer  # type: ignore[import-untyped]


@pytest_asyncio.fixture(scope="session")
async def nats_client() -> AsyncGenerator[NATSClient, None]:
    with NatsContainer() as nats_container:
        client = await nats.connect(nats_container.nats_uri())
        yield client
        await client.close()

