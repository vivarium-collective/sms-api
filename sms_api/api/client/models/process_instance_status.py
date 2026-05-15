from enum import Enum


class ProcessInstanceStatus(str, Enum):
    ACTIVE = "active"
    ENDED = "ended"

    def __str__(self) -> str:
        return str(self.value)
