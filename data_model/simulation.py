import dataclasses
import datetime
from typing import Any
import uuid

from api.data_model.base import BaseClass
    

@dataclasses.dataclass
class Simulation(BaseClass):
    name: str
    duration: float
    document: dict
    results: list = dataclasses.field(default_factory=list)

    @property
    def id(self):
        return self.name + '-' + str(uuid.uuid4())


@dataclasses.dataclass 
class Payload(BaseClass):
    vivarium_id: str
    simulation: Simulation


@dataclasses.dataclass
class Request(Payload):
    pass


@dataclasses.dataclass
class IntervalResponse(BaseClass):
    vivarium_id: str
    interval_id: str
    data: list[dict[str, Any]] = dataclasses.field(default_factory=list)
    

@dataclasses.dataclass
class SimulationRun(BaseClass):
    id: str
    last_updated: str 
    _status: str = "SUBMITTED"
    _data: dict = dataclasses.field(default_factory=dict)
    protocol: str = "secure"  # TODO: this should match WHERE the results were saved to. Users will then use their key and this residence to get the data itself

    @property
    def status(self):
        return self._status
    
    @status.setter
    def status(self, status: str):
        allowed = ['submitted', 'complete', 'failed']
        if status.lower() in allowed and status != self._status:
            self._status = status
        else:
            raise AttributeError(f"{status} is not an allowable status")
    
    @property
    def data(self):
        return self._data
    
    @data.setter
    def data(self, vals):
        key = self.timestamp
        self._data[key] = vals



