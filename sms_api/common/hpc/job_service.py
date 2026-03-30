from abc import ABC, abstractmethod
from dataclasses import dataclass

from sms_api.common.models import JobStatus


@dataclass
class JobStatusInfo:
    """Backend-agnostic job status information."""

    job_id: str
    status: JobStatus
    start_time: str | None = None
    end_time: str | None = None
    exit_code: str | None = None
    error_message: str | None = None


@dataclass
class JobStatusUpdate:
    """Data for updating an HpcRun record's status."""

    job_id: str
    status: JobStatus
    start_time: str | None = None
    end_time: str | None = None
    exit_code: str | None = None
    error_message: str | None = None


class JobStatusService(ABC):
    """Abstract interface for polling job statuses from any backend."""

    @abstractmethod
    async def get_job_statuses(self, job_ids: list[str]) -> list[JobStatusInfo]:
        """Get status information for one or more jobs.

        Args:
            job_ids: List of backend-specific job identifiers.

        Returns:
            List of JobStatusInfo for jobs that were found.
        """
        pass
