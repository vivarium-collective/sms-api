from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import Union

if TYPE_CHECKING:
    from ..models.biocyc_reaction_right_item import BiocycReactionRightItem
    from ..models.biocyc_reaction_enzymatic_reaction import BiocycReactionEnzymaticReaction
    from ..models.biocyc_reaction_left_item import BiocycReactionLeftItem
    from ..models.biocyc_reaction_parent import BiocycReactionParent
    from ..models.biocyc_reaction_ec_number import BiocycReactionEcNumber


T = TypeVar("T", bound="BiocycReaction")


@_attrs_define
class BiocycReaction:
    """
    Attributes:
        id (str):
        orgid (str):
        frameid (str):
        detail (str):
        ec_number (BiocycReactionEcNumber):
        right (list['BiocycReactionRightItem']):
        enzymatic_reaction (BiocycReactionEnzymaticReaction):
        left (list['BiocycReactionLeftItem']):
        parent (Union[Unset, BiocycReactionParent]):
    """

    id: str
    orgid: str
    frameid: str
    detail: str
    ec_number: "BiocycReactionEcNumber"
    right: list["BiocycReactionRightItem"]
    enzymatic_reaction: "BiocycReactionEnzymaticReaction"
    left: list["BiocycReactionLeftItem"]
    parent: Union[Unset, "BiocycReactionParent"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.biocyc_reaction_right_item import BiocycReactionRightItem
        from ..models.biocyc_reaction_enzymatic_reaction import BiocycReactionEnzymaticReaction
        from ..models.biocyc_reaction_left_item import BiocycReactionLeftItem
        from ..models.biocyc_reaction_parent import BiocycReactionParent
        from ..models.biocyc_reaction_ec_number import BiocycReactionEcNumber

        id = self.id

        orgid = self.orgid

        frameid = self.frameid

        detail = self.detail

        ec_number = self.ec_number.to_dict()

        right = []
        for right_item_data in self.right:
            right_item = right_item_data.to_dict()
            right.append(right_item)

        enzymatic_reaction = self.enzymatic_reaction.to_dict()

        left = []
        for left_item_data in self.left:
            left_item = left_item_data.to_dict()
            left.append(left_item)

        parent: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.parent, Unset):
            parent = self.parent.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "orgid": orgid,
            "frameid": frameid,
            "detail": detail,
            "ec_number": ec_number,
            "right": right,
            "enzymatic_reaction": enzymatic_reaction,
            "left": left,
        })
        if parent is not UNSET:
            field_dict["parent"] = parent

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.biocyc_reaction_right_item import BiocycReactionRightItem
        from ..models.biocyc_reaction_enzymatic_reaction import BiocycReactionEnzymaticReaction
        from ..models.biocyc_reaction_left_item import BiocycReactionLeftItem
        from ..models.biocyc_reaction_parent import BiocycReactionParent
        from ..models.biocyc_reaction_ec_number import BiocycReactionEcNumber

        d = dict(src_dict)
        id = d.pop("id")

        orgid = d.pop("orgid")

        frameid = d.pop("frameid")

        detail = d.pop("detail")

        ec_number = BiocycReactionEcNumber.from_dict(d.pop("ec_number"))

        right = []
        _right = d.pop("right")
        for right_item_data in _right:
            right_item = BiocycReactionRightItem.from_dict(right_item_data)

            right.append(right_item)

        enzymatic_reaction = BiocycReactionEnzymaticReaction.from_dict(d.pop("enzymatic_reaction"))

        left = []
        _left = d.pop("left")
        for left_item_data in _left:
            left_item = BiocycReactionLeftItem.from_dict(left_item_data)

            left.append(left_item)

        _parent = d.pop("parent", UNSET)
        parent: Union[Unset, BiocycReactionParent]
        if isinstance(_parent, Unset):
            parent = UNSET
        else:
            parent = BiocycReactionParent.from_dict(_parent)

        biocyc_reaction = cls(
            id=id,
            orgid=orgid,
            frameid=frameid,
            detail=detail,
            ec_number=ec_number,
            right=right,
            enzymatic_reaction=enzymatic_reaction,
            left=left,
            parent=parent,
        )

        biocyc_reaction.additional_properties = d
        return biocyc_reaction

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
