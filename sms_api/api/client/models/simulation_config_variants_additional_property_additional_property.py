from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast
from typing import cast, Union


T = TypeVar("T", bound="SimulationConfigVariantsAdditionalPropertyAdditionalProperty")


@_attrs_define
class SimulationConfigVariantsAdditionalPropertyAdditionalProperty:
    """ """

    additional_properties: dict[str, list[Union[float, int, str]]] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():
            field_dict[prop_name] = []
            for additional_property_item_data in prop:
                additional_property_item: Union[float, int, str]
                additional_property_item = additional_property_item_data
                field_dict[prop_name].append(additional_property_item)

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        simulation_config_variants_additional_property_additional_property = cls()

        additional_properties = {}
        for prop_name, prop_dict in d.items():
            additional_property = []
            _additional_property = prop_dict
            for additional_property_item_data in _additional_property:

                def _parse_additional_property_item(data: object) -> Union[float, int, str]:
                    return cast(Union[float, int, str], data)

                additional_property_item = _parse_additional_property_item(additional_property_item_data)

                additional_property.append(additional_property_item)

            additional_properties[prop_name] = additional_property

        simulation_config_variants_additional_property_additional_property.additional_properties = additional_properties
        return simulation_config_variants_additional_property_additional_property

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> list[Union[float, int, str]]:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: list[Union[float, int, str]]) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
