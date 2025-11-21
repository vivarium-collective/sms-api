"""Tests for the messaging service abstraction with both NATS and Redis implementations."""

import asyncio

import pytest

from sms_api.common.messaging.messaging_service_nats import MessagingServiceNATS
from sms_api.common.messaging.messaging_service_redis import MessagingServiceRedis

# Import fixtures
pytest_plugins = ["tests.fixtures.nats_fixtures", "tests.fixtures.redis_fixtures"]


@pytest.mark.asyncio
async def test_nats_pubsub(
    nats_subscriber_service: MessagingServiceNATS, nats_producer_service: MessagingServiceNATS
) -> None:
    """Test pub/sub functionality with NATS backend."""
    received = asyncio.Event()
    data_holder: dict[str, bytes] = {}

    async def message_handler(data: bytes) -> None:
        data_holder["data"] = data
        received.set()

    assert nats_subscriber_service.is_connected()
    assert nats_producer_service.is_connected()

    await nats_subscriber_service.subscribe("test.subject", callback=message_handler)
    await asyncio.sleep(1.0)  # time for subscription to be set up

    await nats_producer_service.publish("test.subject", b"hello world")

    await asyncio.wait_for(received.wait(), timeout=2.0)
    assert data_holder["data"] == b"hello world"


@pytest.mark.asyncio
async def test_redis_pubsub(
    redis_subscriber_service: MessagingServiceRedis, redis_producer_service: MessagingServiceRedis
) -> None:
    """Test pub/sub functionality with Redis backend."""
    received = asyncio.Event()
    data_holder: dict[str, bytes] = {}

    async def message_handler(data: bytes) -> None:
        data_holder["data"] = data
        received.set()

    assert redis_subscriber_service.is_connected()
    assert redis_producer_service.is_connected()

    await redis_subscriber_service.subscribe("test.subject", callback=message_handler)
    await asyncio.sleep(1.0)  # time for subscription to be set up

    await redis_producer_service.publish("test.subject", b"hello world")

    await asyncio.wait_for(received.wait(), timeout=2.0)
    assert data_holder["data"] == b"hello world"


@pytest.mark.asyncio
async def test_nats_multiple_messages(
    nats_subscriber_service: MessagingServiceNATS, nats_producer_service: MessagingServiceNATS
) -> None:
    """Test receiving multiple messages with NATS backend."""
    messages_received: list[bytes] = []
    expected_count = 10
    received_event = asyncio.Event()

    async def message_handler(data: bytes) -> None:
        messages_received.append(data)
        if len(messages_received) >= expected_count:
            received_event.set()

    await nats_subscriber_service.subscribe("test.subject", callback=message_handler)
    await asyncio.sleep(1.0)  # time for subscription to be set up

    # Send multiple messages
    for i in range(expected_count):
        await nats_producer_service.publish("test.subject", f"message {i}".encode())

    await asyncio.wait_for(received_event.wait(), timeout=5.0)
    assert len(messages_received) == expected_count
    assert messages_received[-1] == b"message 9"


@pytest.mark.asyncio
async def test_redis_multiple_messages(
    redis_subscriber_service: MessagingServiceRedis, redis_producer_service: MessagingServiceRedis
) -> None:
    """Test receiving multiple messages with Redis backend."""
    messages_received: list[bytes] = []
    expected_count = 10
    received_event = asyncio.Event()

    async def message_handler(data: bytes) -> None:
        messages_received.append(data)
        if len(messages_received) >= expected_count:
            received_event.set()

    await redis_subscriber_service.subscribe("test.subject", callback=message_handler)
    await asyncio.sleep(1.0)  # time for subscription to be set up

    # Send multiple messages
    for i in range(expected_count):
        await redis_producer_service.publish("test.subject", f"message {i}".encode())

    await asyncio.wait_for(received_event.wait(), timeout=5.0)
    assert len(messages_received) == expected_count
    assert messages_received[-1] == b"message 9"


@pytest.mark.asyncio
async def test_nats_multiple_channels(
    nats_subscriber_service: MessagingServiceNATS, nats_producer_service: MessagingServiceNATS
) -> None:
    """Test subscribing to multiple channels with NATS backend."""
    channel1_data: dict[str, bytes] = {}
    channel2_data: dict[str, bytes] = {}
    channel1_event = asyncio.Event()
    channel2_event = asyncio.Event()

    async def channel1_handler(data: bytes) -> None:
        channel1_data["data"] = data
        channel1_event.set()

    async def channel2_handler(data: bytes) -> None:
        channel2_data["data"] = data
        channel2_event.set()

    await nats_subscriber_service.subscribe("channel1", callback=channel1_handler)
    await nats_subscriber_service.subscribe("channel2", callback=channel2_handler)
    await asyncio.sleep(1.0)  # time for subscriptions to be set up

    await nats_producer_service.publish("channel1", b"message for channel 1")
    await nats_producer_service.publish("channel2", b"message for channel 2")

    await asyncio.wait_for(asyncio.gather(channel1_event.wait(), channel2_event.wait()), timeout=2.0)

    assert channel1_data["data"] == b"message for channel 1"
    assert channel2_data["data"] == b"message for channel 2"


@pytest.mark.asyncio
async def test_redis_multiple_channels(
    redis_subscriber_service: MessagingServiceRedis, redis_producer_service: MessagingServiceRedis
) -> None:
    """Test subscribing to multiple channels with Redis backend."""
    channel1_data: dict[str, bytes] = {}
    channel2_data: dict[str, bytes] = {}
    channel1_event = asyncio.Event()
    channel2_event = asyncio.Event()

    async def channel1_handler(data: bytes) -> None:
        channel1_data["data"] = data
        channel1_event.set()

    async def channel2_handler(data: bytes) -> None:
        channel2_data["data"] = data
        channel2_event.set()

    await redis_subscriber_service.subscribe("channel1", callback=channel1_handler)
    await redis_subscriber_service.subscribe("channel2", callback=channel2_handler)
    await asyncio.sleep(1.0)  # time for subscriptions to be set up

    await redis_producer_service.publish("channel1", b"message for channel 1")
    await redis_producer_service.publish("channel2", b"message for channel 2")

    await asyncio.wait_for(asyncio.gather(channel1_event.wait(), channel2_event.wait()), timeout=2.0)

    assert channel1_data["data"] == b"message for channel 1"
    assert channel2_data["data"] == b"message for channel 2"


@pytest.mark.asyncio
async def test_nats_connection_status(nats_subscriber_service: MessagingServiceNATS) -> None:
    """Test connection status with NATS backend."""
    assert nats_subscriber_service.is_connected()

    await nats_subscriber_service.disconnect()
    assert not nats_subscriber_service.is_connected()


@pytest.mark.asyncio
async def test_redis_connection_status(redis_subscriber_service: MessagingServiceRedis) -> None:
    """Test connection status with Redis backend."""
    assert redis_subscriber_service.is_connected()

    await redis_subscriber_service.disconnect()
    assert not redis_subscriber_service.is_connected()
