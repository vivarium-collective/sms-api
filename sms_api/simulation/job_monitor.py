import asyncio
import logging
from typing import Any

from async_lru import alru_cache
from nats.aio.client import Client as NATSClient
from nats.aio.msg import Msg

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import JobStatus, WorkerEvent, WorkerEventMessagePayload

logger = logging.getLogger(__name__)


class JobMonitor:
    database_service: DatabaseService
    slurm_service: SlurmService
    nats_client: NATSClient | None = None
    _polling_task: asyncio.Task[None] | None = None
    _stop_event: asyncio.Event

    def __init__(self, nats_client: NATSClient | None, database_service: DatabaseService, slurm_service: SlurmService):
        self.nats_client = nats_client
        self.database_service = database_service
        self.slurm_service = slurm_service
        self._stop_event = asyncio.Event()

    @alru_cache
    async def get_hpcrun_by_correlation_id(self, correlation_id: str) -> int | None:
        return await self.database_service.get_hpcrun_id_by_correlation_id(correlation_id=correlation_id)

    async def subscribe(self) -> None:
        if not get_settings().hpc_has_messaging:
            logger.info("not subscribing to NATS messages, NATS client is not initialized")
            return

        if self.nats_client is None:
            raise RuntimeError("NATS is not available. Cannot submit EcoliSimulation job.")

        subject = get_settings().nats_worker_event_subject
        logger.info(f"Subscribing to NATS messages for subject '{subject}'")

        async def message_handler(msg: Msg) -> Any:
            try:
                subject = msg.subject
                data = msg.data.decode("utf-8")
                logger.debug(f"Received message on subject '{subject}': {data}")
                worker_event_message_payload = WorkerEventMessagePayload.model_validate_json(data)
                worker_event = WorkerEvent.from_message_payload(
                    worker_event_message_payload=worker_event_message_payload
                )
                hpcrun_id = await self.get_hpcrun_by_correlation_id(correlation_id=worker_event.correlation_id)
                if hpcrun_id is None:
                    logger.error(f"No HpcRun found for correlation ID {worker_event.correlation_id}. Skipping event.")
                    return
                _updated_worker_event = await self.database_service.insert_worker_event(
                    worker_event, hpcrun_id=hpcrun_id
                )
            except Exception:
                logger.exception(f"Exception while handling NATS message: {data}")

        await self.nats_client.subscribe(subject=subject, cb=message_handler)
        if self.nats_client.is_connected:
            logger.info("NATS client is connected and subscription is set up.")
        else:
            logger.error("NATS client is not connected.")

    async def start_polling(self, interval_seconds: int = 30) -> None:
        if self._polling_task is not None and not self._polling_task.done():
            logger.warning("Polling task already running.")
            return
        self._stop_event.clear()
        self._polling_task = asyncio.create_task(self._polling_loop(interval_seconds))
        logger.info("Started job status polling task.")

    async def stop_polling(self) -> None:
        if self._stop_event:
            self._stop_event.set()
        if self._polling_task:
            await self._polling_task
            logger.info("Stopped job status polling task.")

    async def _polling_loop(self, interval_seconds: int) -> None:
        while not self._stop_event.is_set():
            try:
                await self.update_running_jobs()
            except Exception:
                logger.exception("Error during job polling")
            await asyncio.sleep(interval_seconds)

    async def update_running_jobs(self) -> None:
        # Fetch all running HpcRun jobs
        running_jobs = await self.database_service.list_running_hpcruns()
        if not running_jobs:
            logger.debug("No running jobs found for polling.")
            return
        job_ids = [job.slurmjobid for job in running_jobs if job.slurmjobid]
        if not job_ids:
            logger.debug("No valid slurm job IDs found in running jobs.")
            return
        slurm_jobs_from_squeue = await self.slurm_service.get_job_status_squeue(job_ids)
        slurm_jobs_from_sacct = await self.slurm_service.get_job_status_sacct(job_ids)
        slurm_job_map = {job.job_id: job for job in slurm_jobs_from_squeue}
        slurm_job_map.update({job.job_id: job for job in slurm_jobs_from_sacct})
        for hpc_run in running_jobs:
            slurm_job = slurm_job_map.get(hpc_run.slurmjobid)
            if not slurm_job or not slurm_job.job_state:
                continue
            new_status = JobStatus(slurm_job.job_state.lower())
            if new_status == hpc_run.status:
                logger.debug(f"HpcRun {hpc_run.database_id} is still running with status {new_status}")
                continue
            if hpc_run.status != new_status:
                await self.database_service.update_hpcrun_status(hpcrun_id=hpc_run.database_id, new_slurm_job=slurm_job)
                logger.info(f"Updated HpcRun {hpc_run.database_id} status to {new_status}")

    async def close(self) -> None:
        await self.stop_polling()
        logger.debug("Closing NATS client connection")

        if self.nats_client is not None:
            await self.nats_client.close()
