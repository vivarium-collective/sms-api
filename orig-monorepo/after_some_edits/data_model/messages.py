import dataclasses
from typing import Any

from sms_api.data_model.base import BaseClass, BaseModel


@dataclasses.dataclass
class Packet(BaseClass):
    action: str
    user: str
    message: dict[str, Any]


class MessageToRoomModel(BaseModel):
    user_id: str
    message: str
    room_id: str


class RegisterToRoom(BaseModel):
    user_id: str
    room_id: str
