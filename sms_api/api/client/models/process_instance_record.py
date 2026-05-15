from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.process_instance_status import ProcessInstanceStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.process_instance_record_config import ProcessInstanceRecordConfig


T = TypeVar("T", bound="ProcessInstanceRecord")


@_attrs_define
class ProcessInstanceRecord:
    """
    Attributes:
        database_id (int):
        process_id (str):
        process_name (str):
        config (ProcessInstanceRecordConfig):
        status (ProcessInstanceStatus):
        created_at (str):
        ended_at (Union[None, Unset, str]):
    """

    database_id: int
    process_id: str
    process_name: str
    config: "ProcessInstanceRecordConfig"
    status: ProcessInstanceStatus
    created_at: str
    ended_at: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        database_id = self.database_id

        process_id = self.process_id

        process_name = self.process_name

        config = self.config.to_dict()

        status = self.status.value

        created_at = self.created_at

        ended_at: Union[None, Unset, str]
        if isinstance(self.ended_at, Unset):
            ended_at = UNSET
        else:
            ended_at = self.ended_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "database_id": database_id,
                "process_id": process_id,
                "process_name": process_name,
                "config": config,
                "status": status,
                "created_at": created_at,
            }
        )
        if ended_at is not UNSET:
            field_dict["ended_at"] = ended_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.process_instance_record_config import ProcessInstanceRecordConfig

        d = dict(src_dict)
        database_id = d.pop("database_id")

        process_id = d.pop("process_id")

        process_name = d.pop("process_name")

        config = ProcessInstanceRecordConfig.from_dict(d.pop("config"))

        status = ProcessInstanceStatus(d.pop("status"))

        created_at = d.pop("created_at")

        def _parse_ended_at(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        ended_at = _parse_ended_at(d.pop("ended_at", UNSET))

        process_instance_record = cls(
            database_id=database_id,
            process_id=process_id,
            process_name=process_name,
            config=config,
            status=status,
            created_at=created_at,
            ended_at=ended_at,
        )

        process_instance_record.additional_properties = d
        return process_instance_record

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
