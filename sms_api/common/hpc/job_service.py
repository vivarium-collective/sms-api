from dataclasses import dataclass

from sms_api.common.models import JobStatus


@dataclass
class JobStatusUpdate:
    """Backend-agnostic data for updating an HpcRun record's status."""

    job_id: str
    status: JobStatus
    start_time: str | None = None
    end_time: str | None = None
    exit_code: str | None = None
    error_message: str | None = None
