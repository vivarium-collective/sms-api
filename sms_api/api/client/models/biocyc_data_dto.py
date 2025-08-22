from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.biocyc_data_dto_data import BiocycDataDTOData


T = TypeVar("T", bound="BiocycDataDTO")


@_attrs_define
class BiocycDataDTO:
    """
    Attributes:
        obj_id (str):
        org_id (str):
        data (BiocycDataDTOData):
    """

    obj_id: str
    org_id: str
    data: "BiocycDataDTOData"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.biocyc_data_dto_data import BiocycDataDTOData

        obj_id = self.obj_id

        org_id = self.org_id

        data = self.data.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "obj_id": obj_id,
            "org_id": org_id,
            "data": data,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.biocyc_data_dto_data import BiocycDataDTOData

        d = dict(src_dict)
        obj_id = d.pop("obj_id")

        org_id = d.pop("org_id")

        data = BiocycDataDTOData.from_dict(d.pop("data"))

        biocyc_data_dto = cls(
            obj_id=obj_id,
            org_id=org_id,
            data=data,
        )

        biocyc_data_dto.additional_properties = d
        return biocyc_data_dto

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
