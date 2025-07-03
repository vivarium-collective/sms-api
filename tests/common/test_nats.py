import asyncio
import threading

import nats
import pytest
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
import uvloop
from testcontainers.nats import NatsContainer


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


loop = uvloop.new_event_loop()
thread = threading.Thread(target=loop.run_forever, daemon=True)
thread.start()

def call_async(coro):
    """Submit a coroutine to run in the background event loop."""
    return asyncio.run_coroutine_threadsafe(coro, loop)


async def run_pubsub(subscriber: NATSClient, producer: NATSClient, received: asyncio.Event, data_holder: dict):
    async def message_handler(msg: Msg):
        data_holder["data"] = msg.data
        received.set()

    await subscriber.subscribe("test.subject", cb=message_handler)
    await asyncio.sleep(1.0)  # wait for subscription to be ready
    await producer.publish("test.subject", b"hello world")
    await asyncio.wait_for(received.wait(), timeout=0.1)


def test_sync_pubsub():
    # 1. Launch the container synchronously
    with NatsContainer() as nats_container:
        uri = nats_container.nats_uri()

        # 2. Create clients
        subscriber_future = call_async(nats.connect(uri, verbose=True))
        producer_future = call_async(nats.connect(uri, verbose=True))

        subscriber = subscriber_future.result(timeout=5)
        producer = producer_future.result(timeout=5)
        assert subscriber.is_connected
        assert producer.is_connected

        # 3. Run test logic
        received = asyncio.Event()
        data_holder = {}

        # async def message_handler(msg: Msg):
        #     data_holder["data"] = msg.data
        #     received.set()

        # async def run_pubsub():
        #     await subscriber.subscribe("test.subject", cb=message_handler)
        #     await asyncio.sleep(1.0)  # wait for subscription to be ready
        #     await producer.publish("test.subject", b"hello world")
        #     await asyncio.wait_for(received.wait(), timeout=0.1)

        call_async(run_pubsub(subscriber, producer, received, data_holder)).result(timeout=5)
        # call_async(run_pubsub()).result(timeout=5)

        assert data_holder["data"] == b"hello world"
        print(f'Data holder: {data_holder}')

        # 4. Cleanup
        call_async(subscriber.close()).result(timeout=2)
        call_async(producer.close()).result(timeout=2)
