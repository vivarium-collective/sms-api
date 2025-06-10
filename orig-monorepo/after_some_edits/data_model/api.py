from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from sms_api.data_model.base import BaseClass


class Base(BaseModel):
    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)


@dataclass
class ISimulationRequest(BaseClass):
    experiment_id: str | None = None
    last_update: str | None = None
    cookie: str = "session_user"

    def __post_init__(self) -> None:
        if self.last_update is None:
            self.refresh_timestamp()

    def refresh_timestamp(self) -> None:
        self.last_update = self.timestamp()


# -- requests -- #
@dataclass
class WCMSimulationRequest(ISimulationRequest):
    total_time: float = 10.0
    time_step: float = 1.0
    start_time: float = 0.1111
    simulation_id: str | None = None


# -- responses -- #
@dataclass
class BulkMoleculeData(BaseClass):
    id: str
    count: int
    submasses: list[str]


@dataclass
class ListenerData(BaseClass):
    fba_results: dict = field(default_factory=dict)
    atp: dict = field(default_factory=dict)
    equilibrium_listener: dict = field(default_factory=dict)


@dataclass
class WCMIntervalData(BaseClass):
    bulk: list[BulkMoleculeData]
    listeners: ListenerData
    # TODO: add more!


@dataclass
class WCMIntervalResponse(BaseClass):
    experiment_id: str
    interval_id: str
    data: WCMIntervalData
