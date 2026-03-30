import asyncio
import logging

from async_lru import alru_cache

from sms_api.common.hpc.job_service import JobStatusService, JobStatusUpdate
from sms_api.common.messaging.messaging_service import MessagingService
from sms_api.config import get_settings
from sms_api.simulation.database_service import DatabaseService
from sms_api.simulation.models import WorkerEvent, WorkerEventMessagePayload

logger = logging.getLogger(__name__)


class JobScheduler:
    database_service: DatabaseService
    job_status_service: JobStatusService
    messaging_service: MessagingService
    _polling_task: asyncio.Task[None] | None = None
    _stop_event: asyncio.Event

    def __init__(
        self,
        messaging_service: MessagingService,
        database_service: DatabaseService,
        job_status_service: JobStatusService,
    ):
        self.messaging_service = messaging_service
        self.database_service = database_service
        self.job_status_service = job_status_service
        self._stop_event = asyncio.Event()

    @alru_cache
    async def get_hpcrun_by_correlation_id(self, correlation_id: str) -> int | None:
        return await self.database_service.get_hpcrun_id_by_correlation_id(correlation_id=correlation_id)

    async def subscribe(self) -> None:
        channel = get_settings().redis_channel
        logger.info(f"Subscribing to messaging service for channel '{channel}'")

        async def message_handler(data: bytes) -> None:
            try:
                data_str = data.decode("utf-8")
                logger.debug(f"Received message on channel '{channel}': {data_str}")
                worker_event_message_payload = WorkerEventMessagePayload.model_validate_json(data_str)
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
                logger.exception(f"Exception while handling message: {data!r}")

        await self.messaging_service.subscribe(subject=channel, callback=message_handler)
        if self.messaging_service.is_connected():
            logger.info("Messaging service is connected and subscription is set up.")
        else:
            logger.error("Messaging service is not connected.")

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
        # Fetch all active (PENDING or RUNNING) HpcRun jobs
        running_jobs = await self.database_service.list_active_hpcruns()
        if not running_jobs:
            logger.debug("No active jobs found for polling.")
            return

        # Collect external job IDs, skipping any that don't have one
        job_id_to_hpc_run: dict[str, list[int]] = {}  # external_job_id -> [hpcrun database_ids]
        for job in running_jobs:
            try:
                ext_id = job.external_job_id
            except ValueError:
                continue
            job_id_to_hpc_run.setdefault(ext_id, []).append(job.database_id)

        if not job_id_to_hpc_run:
            logger.debug("No valid job IDs found in running jobs.")
            return

        # Query all statuses in one call
        status_infos = await self.job_status_service.get_job_statuses(list(job_id_to_hpc_run.keys()))
        status_map = {info.job_id: info for info in status_infos}

        for hpc_run in running_jobs:
            try:
                ext_id = hpc_run.external_job_id
            except ValueError:
                continue
            info = status_map.get(ext_id)
            if not info:
                continue
            if info.status == hpc_run.status:
                logger.debug(f"HpcRun {hpc_run.database_id} is still {info.status}")
                continue
            update = JobStatusUpdate(
                job_id=info.job_id,
                status=info.status,
                start_time=info.start_time,
                end_time=info.end_time,
                exit_code=info.exit_code,
                error_message=info.error_message,
            )
            await self.database_service.update_hpcrun_status(hpcrun_id=hpc_run.database_id, update=update)
            logger.info(f"Updated HpcRun {hpc_run.database_id} status to {info.status}")

    async def close(self) -> None:
        await self.stop_polling()
        logger.debug("Closing messaging service connection")
        await self.messaging_service.disconnect()
