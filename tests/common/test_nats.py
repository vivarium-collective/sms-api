import asyncio

import pytest
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg

# from nats.js import JetStreamContext


# @pytest.mark.asyncio
# async def test_jetstream_pubsub(jetstream_client: JetStreamContext) -> None:
#     # Get a context to produce and consume messages from NATS JetStream
#     js = jetstream_client
#
#     # Create a stream named 'events' and with subjects matching 'events.*'
#     # 'events' will be a default stream that all events will be sent to
#     # Storage parameter can be set to 'NONE' for no storage, 'FILE' for file based storage,
#                                                         or 'MEMORY' for memory based storage
#     await js.add_stream(name="events", subjects=["events.*"], storage="memory")
#
#     # Publish 6 messages to the JetStream
#     await js.publish("events.page_loaded", b"")
#     await js.publish("events.mouse_clicked", b"")
#     await js.publish("events.mouse_clicked", b"")
#     await js.publish("events.page_loaded", b"")
#     await js.publish("events.mouse_clicked", b"")
#     await js.publish("events.input_focused", b"")
#     print("published 6 messages", "\n")
#
#     # Check the number of messages in the stream using streams_info
#     # StreamState includes the total number of messages in the stream
#     print(await js.streams_info(), "\n")
#
#     # Update the 'events' stream to have a maximum of 10 messages
#     await js.update_stream(name="events", subjects=["events.*"], max_msgs=10)
#     print("set max messages to 10", "\n")
#
#     # Check the number of messages in the stream using streams_info
#     # StreamState includes the total number of messages in the stream
#     print(await js.streams_info(), "\n")
#
#     # Update the 'events' stream to have a maximum of 300 bytes
#     await js.update_stream(name="events", subjects=["events.*"], max_msgs=10, max_bytes=300)
#     print("set max bytes to 300", "\n")
#
#     # Check the number of messages in the stream using streams_info
#     # StreamState includes the total number of messages in the stream
#     print(await js.streams_info(), "\n")
#
#     # Update the 'events' stream to have a maximum age of 0.1 seconds
#     await js.update_stream(name="events", subjects=["events.*"], max_msgs=10, max_bytes=300, max_age=0.1)
#     print("set max age to 0.1 second", "\n")
#
#     # Check the number of messages in the stream using streams_info
#     # StreamState includes the total number of messages in the stream
#     print(await js.streams_info(), "\n")
#
#     # Sleep for 10 seconds to allow messages to expire
#     await asyncio.sleep(10)
#
#     # Check the number of messages in the stream using streams_info
#     # StreamState includes the total number of messages in the stream
#     print(await js.streams_info())
#
#     # Delete the 'events' stream
#     await js.delete_stream("events")


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
