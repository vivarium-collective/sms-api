import pytest
from types_aiobotocore_sqs.client import SQSClient as AsyncSQSClient
from types_boto3_sqs.client import SQSClient


def test_send_and_receive(sqs_client: SQSClient, sqs_queue_url: str) -> None:
    # send
    send_resp = sqs_client.send_message(
        QueueUrl=sqs_queue_url,
        MessageBody="hello-localstack",
    )
    assert "MessageId" in send_resp

    # receive
    recv = sqs_client.receive_message(
        QueueUrl=sqs_queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=1,
        VisibilityTimeout=5,
    )
    msgs = recv.get("Messages", [])
    assert len(msgs) == 1
    assert msgs[0]["Body"] == "hello-localstack"

    # delete
    sqs_client.delete_message(
        QueueUrl=sqs_queue_url,
        ReceiptHandle=msgs[0]["ReceiptHandle"],
    )

pytestmark = pytest.mark.asyncio

async def test_send_and_receive_async(
    async_sqs_client: AsyncSQSClient, async_sqs_queue_url: str
) -> None:
    # send
    send_resp = await async_sqs_client.send_message(
        QueueUrl=async_sqs_queue_url,
        MessageBody="hello-localstack-async",
    )
    assert "MessageId" in send_resp

    # receive (short poll)
    recv = await async_sqs_client.receive_message(
        QueueUrl=async_sqs_queue_url,
        MaxNumberOfMessages=1,
        WaitTimeSeconds=1,
        VisibilityTimeout=5,
    )
    msgs = recv.get("Messages", [])
    assert len(msgs) == 1
    assert msgs[0]["Body"] == "hello-localstack-async"

    # delete
    await async_sqs_client.delete_message(
        QueueUrl=async_sqs_queue_url,
        ReceiptHandle=msgs[0]["ReceiptHandle"],
    )
#
#
# import json
# import os
# from typing import Any
#
# import boto3
# from types_boto3_sqs import SQSClient
#
# sqs: SQSClient = boto3.client("sqs", region_name=os.getenv("AWS_REGION","us-east-1"))
# QUEUE_URL = os.environ["SQS_QUEUE_URL"]
#
# def publish(event_type: str, job_id: str, payload: dict[str, Any] | None =None, status: str | None=None) -> None:
#     msg = {
#         "eventType": event_type,
#         "jobId": job_id,
#         "status": status or "INFO",
#         "ts": __import__("time").time(),
#         "payload": payload or {},
#     }
#     sqs.send_message(QueueUrl=QUEUE_URL, MessageBody=json.dumps(msg))
#
#
# """bash
# aws sqs send-message \
#   --queue-url "$SQS_QUEUE_URL" \
#   --message-body '{"eventType":"job.status","jobId":"123","status":"COMPLETED","ts":1732212345}'
# """