from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="PackageAuditRequest")


@_attrs_define
class PackageAuditRequest:
    """
    Attributes:
        target (str): Git repo URL or local filesystem path
        ref (Union[None, Unset, str]): Git branch/tag/commit (optional)
        run_install (Union[Unset, bool]): Run pip install smoke test Default: False.
    """

    target: str
    ref: Union[None, Unset, str] = UNSET
    run_install: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        target = self.target

        ref: Union[None, Unset, str]
        if isinstance(self.ref, Unset):
            ref = UNSET
        else:
            ref = self.ref

        run_install = self.run_install

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "target": target,
            }
        )
        if ref is not UNSET:
            field_dict["ref"] = ref
        if run_install is not UNSET:
            field_dict["run_install"] = run_install

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        target = d.pop("target")

        def _parse_ref(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        ref = _parse_ref(d.pop("ref", UNSET))

        run_install = d.pop("run_install", UNSET)

        package_audit_request = cls(
            target=target,
            ref=ref,
            run_install=run_install,
        )

        package_audit_request.additional_properties = d
        return package_audit_request

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
