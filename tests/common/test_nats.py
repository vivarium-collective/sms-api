import threading
import asyncio
import nats
import pytest
import uvloop
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
from nats.js.api import ConsumerConfig  # if needed
from nats.aio.errors import ErrConnectionClosed
from testcontainers.nats import NatsContainer

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

# --- Setup event loop in background thread
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


def test_nats_pubsub():
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
