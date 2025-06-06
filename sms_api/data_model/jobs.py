import enum

from data_model.requests import SimulationRequest
from pydantic import BaseModel, ConfigDict, Field


class SimulationRunStatuses(enum.EnumType):
    submitted = "SUBMITTED"
    running = "RUNNING"
    complete = "COMPLETE"
    failed = "FAILED"


class SimulationRun(BaseModel):
    simulation_id: str
    status: str
    request: SimulationRequest | None = Field(default=None)
    results: dict | None = Field(default=None)
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)
