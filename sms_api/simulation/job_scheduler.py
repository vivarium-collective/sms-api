import logging
from typing import Any

from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg
from sqlalchemy.ext.asyncio import AsyncSession

from sms_api.simulation.models import WorkerEvent
from sms_api.simulation.simulation_database import SimulationDatabaseService

logger = logging.getLogger(__name__)


class JobScheduler:
    nats_client: NATSClient
    database_service: SimulationDatabaseService

    def __init__(self, nats_client: NATSClient, database_service: SimulationDatabaseService):
        self.nats_client = nats_client
        self.database_service = database_service

    async def subscribe(self, session: AsyncSession, simulator_id: int) -> None:
        logger.debug(f"Subscribing to NATS messages for simulator_id: {simulator_id}")

        async def message_handler(msg: Msg) -> Any:
            subject = msg.subject
            data = msg.data.decode("utf-8")
            logger.debug(f"Received message on subject '{subject}': {data}")
            worker_event = WorkerEvent.model_validate_json(data)
            _updated_worker_event = await self.database_service.insert_worker_event(worker_event)

        await self.nats_client.subscribe(f"simulator.{simulator_id}", cb=message_handler)

    async def close(self) -> None:
        logger.debug("Closing NATS client connection")
        await self.nats_client.close()
