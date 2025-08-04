from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union

if TYPE_CHECKING:
    from ..models.worker_event_mass import WorkerEventMass


T = TypeVar("T", bound="WorkerEvent")


@_attrs_define
class WorkerEvent:
    """
    Attributes:
        correlation_id (str):
        sequence_number (int):
        mass (WorkerEventMass):
        time (float):
        database_id (Union[None, Unset, int]):
        created_at (Union[None, Unset, str]):
        hpcrun_id (Union[None, Unset, int]):
    """

    correlation_id: str
    sequence_number: int
    mass: "WorkerEventMass"
    time: float
    database_id: Union[None, Unset, int] = UNSET
    created_at: Union[None, Unset, str] = UNSET
    hpcrun_id: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.worker_event_mass import WorkerEventMass

        correlation_id = self.correlation_id

        sequence_number = self.sequence_number

        mass = self.mass.to_dict()

        time = self.time

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

        hpcrun_id: Union[None, Unset, int]
        if isinstance(self.hpcrun_id, Unset):
            hpcrun_id = UNSET
        else:
            hpcrun_id = self.hpcrun_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "correlation_id": correlation_id,
            "sequence_number": sequence_number,
            "mass": mass,
            "time": time,
        })
        if database_id is not UNSET:
            field_dict["database_id"] = database_id
        if created_at is not UNSET:
            field_dict["created_at"] = created_at
        if hpcrun_id is not UNSET:
            field_dict["hpcrun_id"] = hpcrun_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.worker_event_mass import WorkerEventMass

        d = dict(src_dict)
        correlation_id = d.pop("correlation_id")

        sequence_number = d.pop("sequence_number")

        mass = WorkerEventMass.from_dict(d.pop("mass"))

        time = d.pop("time")

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

        def _parse_hpcrun_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        hpcrun_id = _parse_hpcrun_id(d.pop("hpcrun_id", UNSET))

        worker_event = cls(
            correlation_id=correlation_id,
            sequence_number=sequence_number,
            mass=mass,
            time=time,
            database_id=database_id,
            created_at=created_at,
            hpcrun_id=hpcrun_id,
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
