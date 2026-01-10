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

    WAITING = "waiting"
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DataId(BaseModel):
    scope: str
    label: str
    timestamp: str

    def str(self) -> str:
        return f"{self.scope}-{self.label}-{self.timestamp}"
