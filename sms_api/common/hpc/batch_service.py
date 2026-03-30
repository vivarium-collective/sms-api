import logging
from typing import Any

import aioboto3

from sms_api.common.hpc.job_service import JobStatusInfo, JobStatusService
from sms_api.common.models import JobStatus

logger = logging.getLogger(__name__)


class AwsBatchService(JobStatusService):
    """AWS Batch job submission and status service."""

    def __init__(self, region: str = "us-east-1") -> None:
        self._region = region
        self._session = aioboto3.Session()

    async def submit_job(
        self,
        job_name: str,
        job_definition: str,
        job_queue: str,
        container_overrides: dict[str, Any] | None = None,
        parameters: dict[str, str] | None = None,
        tags: dict[str, str] | None = None,
    ) -> str:
        """Submit a job to AWS Batch.

        Returns:
            The Batch job UUID as a string.
        """
        kwargs: dict[str, Any] = {
            "jobName": job_name,
            "jobDefinition": job_definition,
            "jobQueue": job_queue,
        }
        if container_overrides:
            kwargs["containerOverrides"] = container_overrides
        if parameters:
            kwargs["parameters"] = parameters
        if tags:
            kwargs["tags"] = tags

        async with self._session.client("batch", region_name=self._region) as client:
            response = await client.submit_job(**kwargs)
            job_id: str = response["jobId"]
            logger.info(f"Submitted AWS Batch job: {job_name} -> {job_id}")
            return job_id

    async def get_job_statuses(self, job_ids: list[str]) -> list[JobStatusInfo]:
        """Get status for one or more AWS Batch jobs via describe_jobs."""
        if not job_ids:
            return []

        results: list[JobStatusInfo] = []
        # describe_jobs accepts up to 100 job IDs at a time
        for i in range(0, len(job_ids), 100):
            chunk = job_ids[i : i + 100]
            async with self._session.client("batch", region_name=self._region) as client:
                response = await client.describe_jobs(jobs=chunk)

            for job in response.get("jobs", []):
                batch_status = job.get("status", "UNKNOWN")
                status = JobStatus.from_batch_state(batch_status)

                start_time = None
                if job.get("startedAt"):
                    start_time = str(job["startedAt"])

                end_time = None
                if job.get("stoppedAt"):
                    end_time = str(job["stoppedAt"])

                exit_code = None
                error_message = None
                container = job.get("container", {})
                if container.get("exitCode") is not None:
                    exit_code = str(container["exitCode"])
                if container.get("reason"):
                    error_message = container["reason"]
                if status == JobStatus.FAILED and not error_message:
                    error_message = job.get("statusReason", f"Batch state: {batch_status}")

                results.append(
                    JobStatusInfo(
                        job_id=job["jobId"],
                        status=status,
                        start_time=start_time,
                        end_time=end_time,
                        exit_code=exit_code,
                        error_message=error_message,
                    )
                )

        return results
