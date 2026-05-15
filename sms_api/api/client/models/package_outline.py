from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.package_type import PackageType

if TYPE_CHECKING:
    from ..models.bi_graph_compute_outline import BiGraphComputeOutline


T = TypeVar("T", bound="PackageOutline")


@_attrs_define
class PackageOutline:
    """
    Attributes:
        package_type (PackageType):
        name (str):
        compute (list['BiGraphComputeOutline']):
    """

    package_type: PackageType
    name: str
    compute: list["BiGraphComputeOutline"]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        package_type = self.package_type.value

        name = self.name

        compute = []
        for compute_item_data in self.compute:
            compute_item = compute_item_data.to_dict()
            compute.append(compute_item)

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "package_type": package_type,
                "name": name,
                "compute": compute,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.bi_graph_compute_outline import BiGraphComputeOutline

        d = dict(src_dict)
        package_type = PackageType(d.pop("package_type"))

        name = d.pop("name")

        compute = []
        _compute = d.pop("compute")
        for compute_item_data in _compute:
            compute_item = BiGraphComputeOutline.from_dict(compute_item_data)

            compute.append(compute_item)

        package_outline = cls(
            package_type=package_type,
            name=name,
            compute=compute,
        )

        package_outline.additional_properties = d
        return package_outline

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
