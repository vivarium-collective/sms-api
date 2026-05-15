from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="ContainerizationFileRepr")


@_attrs_define
class ContainerizationFileRepr:
    """Wraps a rendered container-definition file as text.

    A separate model rather than a bare ``str`` so it round-trips cleanly
    through Pydantic-backed DB persistence and the OpenAPI surface.

        Attributes:
            representation (str):
    """

    representation: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        representation = self.representation

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "representation": representation,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        representation = d.pop("representation")

        containerization_file_repr = cls(
            representation=representation,
        )

        containerization_file_repr.additional_properties = d
        return containerization_file_repr

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
