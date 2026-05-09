from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.process_initialize_request_config import ProcessInitializeRequestConfig


T = TypeVar("T", bound="ProcessInitializeRequest")


@_attrs_define
class ProcessInitializeRequest:
    """
    Attributes:
        config (Union[Unset, ProcessInitializeRequestConfig]): Config dict matching the process config_schema.
    """

    config: Union[Unset, "ProcessInitializeRequestConfig"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        config: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.config, Unset):
            config = self.config.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if config is not UNSET:
            field_dict["config"] = config

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.process_initialize_request_config import ProcessInitializeRequestConfig

        d = dict(src_dict)
        _config = d.pop("config", UNSET)
        config: Union[Unset, ProcessInitializeRequestConfig]
        if isinstance(_config, Unset):
            config = UNSET
        else:
            config = ProcessInitializeRequestConfig.from_dict(_config)

        process_initialize_request = cls(
            config=config,
        )

        process_initialize_request.additional_properties = d
        return process_initialize_request

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
