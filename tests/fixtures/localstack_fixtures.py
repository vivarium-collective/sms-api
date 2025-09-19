import uuid
from dataclasses import dataclass
from typing import AsyncGenerator
from typing import Generator

import aiobotocore
import boto3
import pytest
import pytest_asyncio
from aiobotocore.session import AioSession
from testcontainers.localstack import LocalStackContainer  # type: ignore
from types_aiobotocore_sqs.client import SQSClient as AsyncSQSClient
from types_boto3_sqs.client import SQSClient
from types_boto3_sqs.type_defs import CreateQueueResultTypeDef

AWS_REGION = "us-east-1"

# give me a simple data structure for holding the localstack connection info
@dataclass
class LocalStackInfo:
    endpoint_url: str
    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str

@pytest.fixture(scope="session")
def localstack_info() -> Generator[LocalStackInfo, None, None]:
    """
    Spins up LocalStack in Docker (SQS only) for the whole test session.
    """
    container = (
        LocalStackContainer(image="localstack/localstack:4.8.0")
        .with_services("sqs")
    )
    container.start()
    try:
        endpoint = container.get_url()  # e.g. http://127.0.0.1:4566
        yield LocalStackInfo(endpoint_url=endpoint, region_name=AWS_REGION, aws_access_key_id="test", aws_secret_access_key="test")
    finally:
        container.stop()


@pytest.fixture
def sqs_client(localstack_info: LocalStackInfo) -> SQSClient:
    """
    Boto3 SQS client configured to talk to LocalStack.
    """
    client = boto3.client(
        "sqs",
        region_name=localstack_info.region_name,
        endpoint_url=localstack_info.endpoint_url,
        aws_access_key_id=localstack_info.aws_access_key_id,
        aws_secret_access_key=localstack_info.aws_secret_access_key,
    )
    # verify client
    client.list_queues()
    return client


@pytest.fixture
def sqs_queue_url(sqs_client: SQSClient) -> Generator[str, None, None]:
    """
    Creates an isolated FIFO-safe queue per test; cleans up after.
    """
    name = f"test-{uuid.uuid4().hex}"
    queue: CreateQueueResultTypeDef = sqs_client.create_queue(QueueName=name)
    url = queue["QueueUrl"]
    try:
        yield url
    finally:
        # Best-effort cleanup (ok if already deleted)
        try:
            sqs_client.delete_queue(QueueUrl=url)
        except Exception:
            pass


@pytest_asyncio.fixture(scope="session")
def _aio_session() -> AioSession:
    # aiobotocore session is lightweight to create
    return aiobotocore.session.get_session()


@pytest_asyncio.fixture
async def async_sqs_client(
    _aio_session: AioSession, localstack_info: LocalStackInfo
) -> AsyncGenerator[AsyncSQSClient, None]:
    """
    Async SQS client talking to LocalStack.
    Properly enters/exits the async context manager to avoid leaked sockets.
    """
    client_cm = _aio_session.create_client(
        "sqs",
        region_name=localstack_info.region_name,
        endpoint_url=localstack_info.endpoint_url,
        aws_access_key_id=localstack_info.aws_access_key_id,
        aws_secret_access_key=localstack_info.aws_secret_access_key,
    )
    client: AsyncSQSClient = await client_cm.__aenter__()
    try:
        # quick sanity check (will raise if endpoint is wrong)
        await client.list_queues()
        yield client
    finally:
        await client_cm.__aexit__(None, None, None)


@pytest_asyncio.fixture
async def async_sqs_queue_url(
    async_sqs_client: AsyncSQSClient,
) -> AsyncGenerator[str, None]:
    """
    Per-test isolated queue; cleans up after.
    """
    name = f"test-{uuid.uuid4().hex}"
    create_resp = await async_sqs_client.create_queue(QueueName=name)
    url = create_resp["QueueUrl"]
    try:
        yield url
    finally:
        try:
            await async_sqs_client.delete_queue(QueueUrl=url)
        except Exception:
            pass