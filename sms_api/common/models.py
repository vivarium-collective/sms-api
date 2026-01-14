from enum import StrEnum
from typing import cast

from pydantic import BaseModel


class StrEnumBase(StrEnum):
    @classmethod
    def keys(cls) -> list[str]:
        return cast(list[str], vars(cls)["_member_names_"])

    @classmethod
    def member_keys(cls) -> list[str]:
        return cast(list[str], vars(cls)["_member_names_"])

    @classmethod
    def values(cls) -> list[str]:
        vals: list[str] = []
        for key in cls.member_keys():
            val = getattr(cls, key, None)
            if val is not None:
                vals.append(val)
        return vals

    @classmethod
    def to_dict(cls) -> dict[str, str]:
        return dict(zip(cls.keys(), cls.values()))

    @classmethod
    def to_list(cls, sort: bool = False) -> list[str]:
        vals = cls.values()
        return sorted(vals) if sort else vals


class JobStatus(StrEnumBase):
    """Shared job status enum for simulations, analyses, and other HPC jobs."""

    UNKNOWN = "unknown"
    WAITING = "waiting"
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    @classmethod
    def from_slurm_state(cls, slurm_state: str) -> "JobStatus":
        """Parse SLURM job state string to JobStatus enum.

        SLURM states can include additional info after the base state,
        e.g., "CANCELLED by 17163" or "FAILED" or "RUNNING".
        This method extracts the base state and maps it to JobStatus.

        Args:
            slurm_state: Raw SLURM job state string (e.g., "RUNNING", "CANCELLED by 17163")

        Returns:
            Corresponding JobStatus enum value, or UNKNOWN if not recognized
        """
        # Extract base state (first word, uppercase)
        base_state = slurm_state.split()[0].upper() if slurm_state else ""
        return _SLURM_STATE_MAP.get(base_state, cls.UNKNOWN)


# Map SLURM job states to JobStatus (defined after enum class)
_SLURM_STATE_MAP: dict[str, JobStatus] = {
    "PENDING": JobStatus.PENDING,
    "RUNNING": JobStatus.RUNNING,
    "COMPLETED": JobStatus.COMPLETED,
    "COMPLETING": JobStatus.RUNNING,  # Job is finishing up
    "FAILED": JobStatus.FAILED,
    "CANCELLED": JobStatus.FAILED,
    "TIMEOUT": JobStatus.FAILED,
    "NODE_FAIL": JobStatus.FAILED,
    "OUT_OF_MEMORY": JobStatus.FAILED,
    "PREEMPTED": JobStatus.FAILED,
}


class DataId(BaseModel):
    scope: str
    label: str
    timestamp: str

    def str(self) -> str:
        return f"{self.scope}-{self.label}-{self.timestamp}"
