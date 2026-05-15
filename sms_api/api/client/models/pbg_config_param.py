from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PbgConfigParam")


@_attrs_define
class PbgConfigParam:
    """A single config parameter for a PBG Process/Step.

    Attributes:
        name (str): Parameter name, e.g. 'rate'
        type_ (Union[Unset, str]): Bigraph-schema type, e.g. 'float' or 'string' Default: 'float'.
        default (Union[None, Unset, bool, float, int, str]): Default value
        description (Union[None, Unset, str]): Human-readable description
    """

    name: str
    type_: Union[Unset, str] = "float"
    default: Union[None, Unset, bool, float, int, str] = UNSET
    description: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        name = self.name

        type_ = self.type_

        default: Union[None, Unset, bool, float, int, str]
        if isinstance(self.default, Unset):
            default = UNSET
        else:
            default = self.default

        description: Union[None, Unset, str]
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "name": name,
            }
        )
        if type_ is not UNSET:
            field_dict["type"] = type_
        if default is not UNSET:
            field_dict["default"] = default
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        name = d.pop("name")

        type_ = d.pop("type", UNSET)

        def _parse_default(data: object) -> Union[None, Unset, bool, float, int, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool, float, int, str], data)

        default = _parse_default(d.pop("default", UNSET))

        def _parse_description(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        description = _parse_description(d.pop("description", UNSET))

        pbg_config_param = cls(
            name=name,
            type_=type_,
            default=default,
            description=description,
        )

        pbg_config_param.additional_properties = d
        return pbg_config_param

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
