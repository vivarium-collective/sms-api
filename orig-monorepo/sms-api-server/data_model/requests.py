import enum
from pydantic import BaseModel, ConfigDict, Field


class SimulationRequest(BaseModel):
    experiment_id: str = "my-experiment"
    total_time: float = 11.11
    time_step: float = 1.0
    start_time: float = 0.0
    framesize: float = 1.0


