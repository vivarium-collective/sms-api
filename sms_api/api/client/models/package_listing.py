from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.package_type import PackageType
from ..types import UNSET, Unset

T = TypeVar("T", bound="PackageListing")


@_attrs_define
class PackageListing:
    """
    Attributes:
        id (int):
        name (str):
        package_type (PackageType):
        num_processes (int):
        num_steps (int):
        created_at (Union[None, Unset, str]):
    """

    id: int
    name: str
    package_type: PackageType
    num_processes: int
    num_steps: int
    created_at: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        id = self.id

        name = self.name

        package_type = self.package_type.value

        num_processes = self.num_processes

        num_steps = self.num_steps

        created_at: Union[None, Unset, str]
        if isinstance(self.created_at, Unset):
            created_at = UNSET
        else:
            created_at = self.created_at

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "id": id,
                "name": name,
                "package_type": package_type,
                "num_processes": num_processes,
                "num_steps": num_steps,
            }
        )
        if created_at is not UNSET:
            field_dict["created_at"] = created_at

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        id = d.pop("id")

        name = d.pop("name")

        package_type = PackageType(d.pop("package_type"))

        num_processes = d.pop("num_processes")

        num_steps = d.pop("num_steps")

        def _parse_created_at(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        created_at = _parse_created_at(d.pop("created_at", UNSET))

        package_listing = cls(
            id=id,
            name=name,
            package_type=package_type,
            num_processes=num_processes,
            num_steps=num_steps,
            created_at=created_at,
        )

        package_listing.additional_properties = d
        return package_listing

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
