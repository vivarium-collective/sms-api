import pytest
from nats.aio.client import Client as NATSClient


@pytest.mark.asyncio
async def test_messaging(nats_client: NATSClient) -> None:
    # get the scheduler object
    # get the initial state of a job
    # send worker messages to the broker
    # get the updated state of the job
    assert nats_client is not None, "NATS client should be initialized"
    assert nats_client.is_connected, "NATS client should be connected"
    # Here you would typically publish a message and the
