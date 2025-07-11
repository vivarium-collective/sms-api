from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from dateutil.parser import isoparse
from typing import cast
from typing import cast, Union
from typing import Union
import datetime

if TYPE_CHECKING:
  from ..models.simulator_version import SimulatorVersion





T = TypeVar("T", bound="RegisteredSimulators")



@_attrs_define
class RegisteredSimulators:
    """
        Attributes:
            versions (list['SimulatorVersion']):
            timestamp (Union[None, Unset, datetime.datetime]):
     """

    versions: list['SimulatorVersion']
    timestamp: Union[None, Unset, datetime.datetime] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.simulator_version import SimulatorVersion
        versions = []
        for versions_item_data in self.versions:
            versions_item = versions_item_data.to_dict()
            versions.append(versions_item)



        timestamp: Union[None, Unset, str]
        if isinstance(self.timestamp, Unset):
            timestamp = UNSET
        elif isinstance(self.timestamp, datetime.datetime):
            timestamp = self.timestamp.isoformat()
        else:
            timestamp = self.timestamp


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "versions": versions,
        })
        if timestamp is not UNSET:
            field_dict["timestamp"] = timestamp

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.simulator_version import SimulatorVersion
        d = dict(src_dict)
        versions = []
        _versions = d.pop("versions")
        for versions_item_data in (_versions):
            versions_item = SimulatorVersion.from_dict(versions_item_data)



            versions.append(versions_item)


        def _parse_timestamp(data: object) -> Union[None, Unset, datetime.datetime]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                timestamp_type_0 = isoparse(data)



                return timestamp_type_0
            except: # noqa: E722
                pass
            return cast(Union[None, Unset, datetime.datetime], data)

        timestamp = _parse_timestamp(d.pop("timestamp", UNSET))


        registered_simulators = cls(
            versions=versions,
            timestamp=timestamp,
        )


        registered_simulators.additional_properties = d
        return registered_simulators

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
