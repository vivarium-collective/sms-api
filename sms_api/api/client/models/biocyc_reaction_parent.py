from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.biocyc_reaction_parent_additional_property import BiocycReactionParentAdditionalProperty


T = TypeVar("T", bound="BiocycReactionParent")


@_attrs_define
class BiocycReactionParent:
    """ """

    additional_properties: dict[str, "BiocycReactionParentAdditionalProperty"] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.biocyc_reaction_parent_additional_property import BiocycReactionParentAdditionalProperty

        field_dict: dict[str, Any] = {}
        for prop_name, prop in self.additional_properties.items():
            field_dict[prop_name] = prop.to_dict()

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.biocyc_reaction_parent_additional_property import BiocycReactionParentAdditionalProperty

        d = dict(src_dict)
        biocyc_reaction_parent = cls()

        additional_properties = {}
        for prop_name, prop_dict in d.items():
            additional_property = BiocycReactionParentAdditionalProperty.from_dict(prop_dict)

            additional_properties[prop_name] = additional_property

        biocyc_reaction_parent.additional_properties = additional_properties
        return biocyc_reaction_parent

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> "BiocycReactionParentAdditionalProperty":
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: "BiocycReactionParentAdditionalProperty") -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
