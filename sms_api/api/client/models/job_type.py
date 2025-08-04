from enum import Enum


class JobType(str, Enum):
    BUILD_IMAGE = "build_image"
    PARCA = "parca"
    SIMULATION = "simulation"

    def __str__(self) -> str:
        return str(self.value)
