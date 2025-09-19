from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.config_overrides import ConfigOverrides


T = TypeVar("T", bound="EcoliExperimentRequestDTO")


@_attrs_define
class EcoliExperimentRequestDTO:
    """
    Attributes:
        config_id (str):
        overrides (Union['ConfigOverrides', None, Unset]):
    """

    config_id: str
    overrides: Union["ConfigOverrides", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.config_overrides import ConfigOverrides

        config_id = self.config_id

        overrides: Union[None, Unset, dict[str, Any]]
        if isinstance(self.overrides, Unset):
            overrides = UNSET
        elif isinstance(self.overrides, ConfigOverrides):
            overrides = self.overrides.to_dict()
        else:
            overrides = self.overrides

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "config_id": config_id,
            }
        )
        if overrides is not UNSET:
            field_dict["overrides"] = overrides

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.config_overrides import ConfigOverrides

        d = dict(src_dict)
        config_id = d.pop("config_id")

        def _parse_overrides(data: object) -> Union["ConfigOverrides", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                overrides_type_0 = ConfigOverrides.from_dict(data)

                return overrides_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ConfigOverrides", None, Unset], data)

        overrides = _parse_overrides(d.pop("overrides", UNSET))

        ecoli_experiment_request_dto = cls(
            config_id=config_id,
            overrides=overrides,
        )

        ecoli_experiment_request_dto.additional_properties = d
        return ecoli_experiment_request_dto

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
