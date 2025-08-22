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
    from ..models.biocyc_data_request import BiocycDataRequest
    from ..models.biocyc_data_data import BiocycDataData


T = TypeVar("T", bound="BiocycData")


@_attrs_define
class BiocycData:
    """
    Attributes:
        obj_id (str):
        org_id (str):
        data (BiocycDataData):
        request (BiocycDataRequest):
        dest_dirpath (Union[None, Unset, str]):
    """

    obj_id: str
    org_id: str
    data: "BiocycDataData"
    request: "BiocycDataRequest"
    dest_dirpath: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.biocyc_data_request import BiocycDataRequest
        from ..models.biocyc_data_data import BiocycDataData

        obj_id = self.obj_id

        org_id = self.org_id

        data = self.data.to_dict()

        request = self.request.to_dict()

        dest_dirpath: Union[None, Unset, str]
        if isinstance(self.dest_dirpath, Unset):
            dest_dirpath = UNSET
        else:
            dest_dirpath = self.dest_dirpath

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "obj_id": obj_id,
            "org_id": org_id,
            "data": data,
            "request": request,
        })
        if dest_dirpath is not UNSET:
            field_dict["dest_dirpath"] = dest_dirpath

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.biocyc_data_request import BiocycDataRequest
        from ..models.biocyc_data_data import BiocycDataData

        d = dict(src_dict)
        obj_id = d.pop("obj_id")

        org_id = d.pop("org_id")

        data = BiocycDataData.from_dict(d.pop("data"))

        request = BiocycDataRequest.from_dict(d.pop("request"))

        def _parse_dest_dirpath(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        dest_dirpath = _parse_dest_dirpath(d.pop("dest_dirpath", UNSET))

        biocyc_data = cls(
            obj_id=obj_id,
            org_id=org_id,
            data=data,
            request=request,
            dest_dirpath=dest_dirpath,
        )

        biocyc_data.additional_properties = d
        return biocyc_data

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
