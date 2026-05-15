from enum import Enum


class WrapperStatus(str, Enum):
    AVAILABLE = "available"
    BUILDING = "building"
    FAILED = "failed"
    GENERATING = "generating"
    READY = "ready"
    STORING = "storing"

    def __str__(self) -> str:
        return str(self.value)
