import dataclasses

from api.data_model.simulation import BaseClass


@dataclasses.dataclass
class WebsocketConnection(BaseClass):
    uri: str


@dataclasses.dataclass
class DynamicPacket(BaseClass):
    _params: dict

    def __post_init__(self):
        for name, val in self._params:
            setattr(self, name, val)