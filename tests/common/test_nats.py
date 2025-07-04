import asyncio
import threading

import pytest
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg


@pytest.mark.asyncio
async def test_nats_pubsub(nats_subscriber_client: NATSClient, nats_producer_client: NATSClient) -> None:
    received = asyncio.Event()
    data_holder = {}

    async def message_handler(msg: Msg) -> None:
        data_holder["data"] = msg.data
        received.set()

    assert nats_subscriber_client.is_connected
    assert nats_producer_client.is_connected

    await nats_subscriber_client.subscribe("test.subject", cb=message_handler)
    await asyncio.sleep(1.0)  # time for subscription to be set up

    await nats_producer_client.publish("test.subject", b"hello world")

    await asyncio.wait_for(received.wait(), timeout=0.1)
    assert data_holder["data"] == b"hello world"


def sync_producer(nats_producer_client: NATSClient) -> None:
    # This function uses asyncio.run() internally to send a NATS message
    # Example:
    for i in range(10):
        asyncio.run(nats_producer_client.publish("test.subject", b"hello world " + str(i).encode("utf-8")))


@pytest.mark.asyncio
async def test_sync_producer_with_async_subscriber(
    nats_subscriber_client: NATSClient, nats_producer_client: NATSClient
) -> None:
    received = asyncio.Event()
    data_holder = {}

    async def message_handler(msg: Msg) -> None:
        data_holder["data"] = msg.data
        received.set()

    await nats_subscriber_client.subscribe("test.subject", cb=message_handler)
    await asyncio.sleep(1.0)  # Allow subscription setup

    # Run the synchronous producer in a separate thread
    thread = threading.Thread(target=sync_producer, args=(nats_producer_client,))
    thread.start()
    thread.join()

    await asyncio.wait_for(received.wait(), timeout=1.0)
    assert data_holder["data"] == b"hello world 9"
