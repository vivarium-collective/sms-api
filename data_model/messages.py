import dataclasses

from api.data_model.base import BaseClass, BaseModel


class MessageToRoomModel(BaseModel):
    user_id: str
    message: str
    room_id: str


class RegisterToRoom(BaseModel):
    user_id: str
    room_id: str