import logging
from typing import Any

from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg

from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import WorkerEvent

logger = logging.getLogger(__name__)


class JobScheduler:
    nats_client: NATSClient
    database_service: DatabaseService

    def __init__(self, nats_client: NATSClient, database_service: DatabaseService):
        self.nats_client = nats_client
        self.database_service = database_service

    async def subscribe(self) -> None:
        subject = get_settings().nats_worker_event_subject
        logger.info(f"Subscribing to NATS messages for subject '{subject}'")

        async def message_handler(msg: Msg) -> Any:
            subject = msg.subject
            data = msg.data.decode("utf-8")
            logger.debug(f"Received message on subject '{subject}': {data}")
            worker_event = WorkerEvent.model_validate_json(data)
            _updated_worker_event = await self.database_service.insert_worker_event(worker_event)

        await self.nats_client.subscribe(subject=subject, cb=message_handler)
        if self.nats_client.is_connected:
            logger.info("NATS client is connected and subscription is set up.")
        else:
            logger.error("NATS client is not connected.")

    async def close(self) -> None:
        logger.debug("Closing NATS client connection")
        await self.nats_client.close()
