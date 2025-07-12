from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union






T = TypeVar("T", bound="WorkerEvent")



@_attrs_define
class WorkerEvent:
    """
        Attributes:
            hpcrun_id (int):
            sequence_number (int):
            sim_data (list[list[Union[float, str]]]):
            database_id (Union[None, Unset, int]):
            created_at (Union[None, Unset, str]):
            global_time (Union[None, Unset, float]):
            error_message (Union[None, Unset, str]):
     """

    hpcrun_id: int
    sequence_number: int
    sim_data: list[list[Union[float, str]]]
    database_id: Union[None, Unset, int] = UNSET
    created_at: Union[None, Unset, str] = UNSET
    global_time: Union[None, Unset, float] = UNSET
    error_message: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        hpcrun_id = self.hpcrun_id

        sequence_number = self.sequence_number

        sim_data = []
        for sim_data_item_data in self.sim_data:
            sim_data_item = []
            for sim_data_item_item_data in sim_data_item_data:
                sim_data_item_item: Union[float, str]
                sim_data_item_item = sim_data_item_item_data
                sim_data_item.append(sim_data_item_item)


            sim_data.append(sim_data_item)



        database_id: Union[None, Unset, int]
        if isinstance(self.database_id, Unset):
            database_id = UNSET
        else:
            database_id = self.database_id

        created_at: Union[None, Unset, str]
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        global_time: Union[None, Unset, float]
        if isinstance(self.global_time, Unset):
            global_time = UNSET
        else:
            global_time = self.global_time

        error_message: Union[None, Unset, str]
        if isinstance(self.error_message, Unset):
            error_message = UNSET
        else:
            error_message = self.error_message


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "hpcrun_id": hpcrun_id,
            "sequence_number": sequence_number,
            "sim_data": sim_data,
        })
        if database_id is not UNSET:
            field_dict["database_id"] = database_id
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if global_time is not UNSET:
            field_dict["global_time"] = global_time
        if error_message is not UNSET:
            field_dict["error_message"] = error_message

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        hpcrun_id = d.pop("hpcrun_id")

        sequence_number = d.pop("sequence_number")

        sim_data = []
        _sim_data = d.pop("sim_data")
        for sim_data_item_data in (_sim_data):
            sim_data_item = []
            _sim_data_item = sim_data_item_data
            for sim_data_item_item_data in (_sim_data_item):
                def _parse_sim_data_item_item(data: object) -> Union[float, str]:
                    return cast(Union[float, str], data)

                sim_data_item_item = _parse_sim_data_item_item(sim_data_item_item_data)

                sim_data_item.append(sim_data_item_item)

            sim_data.append(sim_data_item)


        def _parse_database_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        database_id = _parse_database_id(d.pop("database_id", UNSET))


        def _parse_created_at(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))


        def _parse_global_time(data: object) -> Union[None, Unset, float]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, float], data)

        global_time = _parse_global_time(d.pop("global_time", UNSET))


        def _parse_error_message(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        error_message = _parse_error_message(d.pop("error_message", UNSET))


        worker_event = cls(
            hpcrun_id=hpcrun_id,
            sequence_number=sequence_number,
            sim_data=sim_data,
            database_id=database_id,
            created_at=created_at,
            global_time=global_time,
            error_message=error_message,
        )


        worker_event.additional_properties = d
        return worker_event

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
