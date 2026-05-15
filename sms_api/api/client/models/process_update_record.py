from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.process_update_record_result_type_0 import ProcessUpdateRecordResultType0
    from ..models.process_update_record_state import ProcessUpdateRecordState


T = TypeVar("T", bound="ProcessUpdateRecord")


@_attrs_define
class ProcessUpdateRecord:
    """
    Attributes:
        database_id (int):
        process_instance_id (int):
        interval (float):
        state (ProcessUpdateRecordState):
        result (Union['ProcessUpdateRecordResultType0', None]):
        called_at (str):
    """

    database_id: int
    process_instance_id: int
    interval: float
    state: "ProcessUpdateRecordState"
    result: Union["ProcessUpdateRecordResultType0", None]
    called_at: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.process_update_record_result_type_0 import ProcessUpdateRecordResultType0

        database_id = self.database_id

        process_instance_id = self.process_instance_id

        interval = self.interval

        state = self.state.to_dict()

        result: Union[None, dict[str, Any]]
        if isinstance(self.result, ProcessUpdateRecordResultType0):
            result = self.result.to_dict()
        else:
            result = self.result

        called_at = self.called_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "database_id": database_id,
                "process_instance_id": process_instance_id,
                "interval": interval,
                "state": state,
                "result": result,
                "called_at": called_at,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.process_update_record_result_type_0 import ProcessUpdateRecordResultType0
        from ..models.process_update_record_state import ProcessUpdateRecordState

        d = dict(src_dict)
        database_id = d.pop("database_id")

        process_instance_id = d.pop("process_instance_id")

        interval = d.pop("interval")

        state = ProcessUpdateRecordState.from_dict(d.pop("state"))

        def _parse_result(data: object) -> Union["ProcessUpdateRecordResultType0", None]:
            if data is None:
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                result_type_0 = ProcessUpdateRecordResultType0.from_dict(data)

                return result_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ProcessUpdateRecordResultType0", None], data)

        result = _parse_result(d.pop("result"))

        called_at = d.pop("called_at")

        process_update_record = cls(
            database_id=database_id,
            process_instance_id=process_instance_id,
            interval=interval,
            state=state,
            result=result,
            called_at=called_at,
        )

        process_update_record.additional_properties = d
        return process_update_record

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
