from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.wrapper_status import WrapperStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="PbgWrapperRecord")


@_attrs_define
class PbgWrapperRecord:
    """
    Attributes:
        wrapper_id (int):
        tool_name (str):
        source_repo_url (str):
        source_ref (str):
        status (WrapperStatus):
        created_at (str):
        simulator_id (Union[None, Unset, int]):
        storage_uri (Union[None, Unset, str]):
        error_message (Union[None, Unset, str]):
    """

    wrapper_id: int
    tool_name: str
    source_repo_url: str
    source_ref: str
    status: WrapperStatus
    created_at: str
    simulator_id: Union[None, Unset, int] = UNSET
    storage_uri: Union[None, Unset, str] = UNSET
    error_message: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        wrapper_id = self.wrapper_id

        tool_name = self.tool_name

        source_repo_url = self.source_repo_url

        source_ref = self.source_ref

        status = self.status.value

        created_at = self.created_at

        simulator_id: Union[None, Unset, int]
        if isinstance(self.simulator_id, Unset):
            simulator_id = UNSET
        else:
            simulator_id = self.simulator_id

        storage_uri: Union[None, Unset, str]
        if isinstance(self.storage_uri, Unset):
            storage_uri = UNSET
        else:
            storage_uri = self.storage_uri

        error_message: Union[None, Unset, str]
        if isinstance(self.error_message, Unset):
            error_message = UNSET
        else:
            error_message = self.error_message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "wrapper_id": wrapper_id,
                "tool_name": tool_name,
                "source_repo_url": source_repo_url,
                "source_ref": source_ref,
                "status": status,
                "created_at": created_at,
            }
        )
        if simulator_id is not UNSET:
            field_dict["simulator_id"] = simulator_id
        if storage_uri is not UNSET:
            field_dict["storage_uri"] = storage_uri
        if error_message is not UNSET:
            field_dict["error_message"] = error_message

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        wrapper_id = d.pop("wrapper_id")

        tool_name = d.pop("tool_name")

        source_repo_url = d.pop("source_repo_url")

        source_ref = d.pop("source_ref")

        status = WrapperStatus(d.pop("status"))

        created_at = d.pop("created_at")

        def _parse_simulator_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        simulator_id = _parse_simulator_id(d.pop("simulator_id", UNSET))

        def _parse_storage_uri(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        storage_uri = _parse_storage_uri(d.pop("storage_uri", UNSET))

        def _parse_error_message(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        error_message = _parse_error_message(d.pop("error_message", UNSET))

        pbg_wrapper_record = cls(
            wrapper_id=wrapper_id,
            tool_name=tool_name,
            source_repo_url=source_repo_url,
            source_ref=source_ref,
            status=status,
            created_at=created_at,
            simulator_id=simulator_id,
            storage_uri=storage_uri,
            error_message=error_message,
        )

        pbg_wrapper_record.additional_properties = d
        return pbg_wrapper_record

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
