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
    from ..models.biocyc_compound_cml import BiocycCompoundCml
    from ..models.biocyc_compound_parent import BiocycCompoundParent


T = TypeVar("T", bound="BiocycCompound")


@_attrs_define
class BiocycCompound:
    """
    Attributes:
        id (str):
        orgid (str):
        frameid (str):
        detail (str):
        cml (BiocycCompoundCml):
        parent (Union[Unset, BiocycCompoundParent]):
        cls (Union[None, Unset, str]):
    """

    id: str
    orgid: str
    frameid: str
    detail: str
    cml: "BiocycCompoundCml"
    parent: Union[Unset, "BiocycCompoundParent"] = UNSET
    cls: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.biocyc_compound_cml import BiocycCompoundCml
        from ..models.biocyc_compound_parent import BiocycCompoundParent

        id = self.id

        orgid = self.orgid

        frameid = self.frameid

        detail = self.detail

        cml = self.cml.to_dict()

        parent: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.parent, Unset):
            parent = self.parent.to_dict()

        cls: Union[None, Unset, str]
        if isinstance(self.cls, Unset):
            cls = UNSET
        else:
            cls = self.cls

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "id": id,
            "orgid": orgid,
            "frameid": frameid,
            "detail": detail,
            "cml": cml,
        })
        if parent is not UNSET:
            field_dict["parent"] = parent
        if cls is not UNSET:
            field_dict["cls"] = cls

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.biocyc_compound_cml import BiocycCompoundCml
        from ..models.biocyc_compound_parent import BiocycCompoundParent

        d = dict(src_dict)
        id = d.pop("id")

        orgid = d.pop("orgid")

        frameid = d.pop("frameid")

        detail = d.pop("detail")

        cml = BiocycCompoundCml.from_dict(d.pop("cml"))

        _parent = d.pop("parent", UNSET)
        parent: Union[Unset, BiocycCompoundParent]
        if isinstance(_parent, Unset):
            parent = UNSET
        else:
            parent = BiocycCompoundParent.from_dict(_parent)

        def _parse_cls(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        cls = _parse_cls(d.pop("cls", UNSET))

        biocyc_compound = cls(
            id=id,
            orgid=orgid,
            frameid=frameid,
            detail=detail,
            cml=cml,
            parent=parent,
            cls=cls,
        )

        biocyc_compound.additional_properties = d
        return biocyc_compound

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
