from enum import Enum


class JobStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"

    def __str__(self) -> str:
        return str(self.value)
