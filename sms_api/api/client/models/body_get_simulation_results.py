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
  from ..models.settings import Settings
  from ..models.requested_observables import RequestedObservables





T = TypeVar("T", bound="BodyGetSimulationResults")



@_attrs_define
class BodyGetSimulationResults:
    """
        Attributes:
            observable_names (RequestedObservables):
            settings (Union['Settings', None, Unset]):
     """

    observable_names: 'RequestedObservables'
    settings: Union['Settings', None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.settings import Settings
        from ..models.requested_observables import RequestedObservables
        observable_names = self.observable_names.to_dict()

        settings: Union[None, Unset, dict[str, Any]]
        if isinstance(self.settings, Unset):
            settings = UNSET
        elif isinstance(self.settings, Settings):
            settings = self.settings.to_dict()
        else:
            settings = self.settings


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "observable_names": observable_names,
        })
        if settings is not UNSET:
            field_dict["settings"] = settings

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.settings import Settings
        from ..models.requested_observables import RequestedObservables
        d = dict(src_dict)
        observable_names = RequestedObservables.from_dict(d.pop("observable_names"))




        def _parse_settings(data: object) -> Union['Settings', None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                settings_type_0 = Settings.from_dict(data)



                return settings_type_0
            except: # noqa: E722
                pass
            return cast(Union['Settings', None, Unset], data)

        settings = _parse_settings(d.pop("settings", UNSET))


        body_get_simulation_results = cls(
            observable_names=observable_names,
            settings=settings,
        )


        body_get_simulation_results.additional_properties = d
        return body_get_simulation_results

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
