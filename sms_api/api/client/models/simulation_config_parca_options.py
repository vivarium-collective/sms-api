from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.simulation_config_parca_options_additional_property_type_5 import (
        SimulationConfigParcaOptionsAdditionalPropertyType5,
    )


T = TypeVar("T", bound="SimulationConfigParcaOptions")


@_attrs_define
class SimulationConfigParcaOptions:
    """ """

    additional_properties: dict[
        str, Union["SimulationConfigParcaOptionsAdditionalPropertyType5", bool, float, int, list[str], str]
    ] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.simulation_config_parca_options_additional_property_type_5 import (
            SimulationConfigParcaOptionsAdditionalPropertyType5,
        )

        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():
            if isinstance(prop, list):
                field_dict[prop_name] = prop

            elif isinstance(prop, SimulationConfigParcaOptionsAdditionalPropertyType5):
                field_dict[prop_name] = prop.to_dict()
            else:
                field_dict[prop_name] = prop

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.simulation_config_parca_options_additional_property_type_5 import (
            SimulationConfigParcaOptionsAdditionalPropertyType5,
        )

        d = dict(src_dict)
        simulation_config_parca_options = cls()

        additional_properties = {}
        for prop_name, prop_dict in d.items():

            def _parse_additional_property(
                data: object,
            ) -> Union["SimulationConfigParcaOptionsAdditionalPropertyType5", bool, float, int, list[str], str]:
                try:
                    if not isinstance(data, list):
                        raise TypeError()
                    additional_property_type_0 = cast(list[str], data)

                    return additional_property_type_0
                except:  # noqa: E722
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    additional_property_type_5 = SimulationConfigParcaOptionsAdditionalPropertyType5.from_dict(data)

                    return additional_property_type_5
                except:  # noqa: E722
                    pass
                return cast(
                    Union["SimulationConfigParcaOptionsAdditionalPropertyType5", bool, float, int, list[str], str], data
                )

            additional_property = _parse_additional_property(prop_dict)

            additional_properties[prop_name] = additional_property

        simulation_config_parca_options.additional_properties = additional_properties
        return simulation_config_parca_options

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(
        self, key: str
    ) -> Union["SimulationConfigParcaOptionsAdditionalPropertyType5", bool, float, int, list[str], str]:
        return self.additional_properties[key]

    def __setitem__(
        self,
        key: str,
        value: Union["SimulationConfigParcaOptionsAdditionalPropertyType5", bool, float, int, list[str], str],
    ) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
