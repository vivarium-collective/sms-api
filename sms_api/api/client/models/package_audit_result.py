from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.audit_check_result import AuditCheckResult


T = TypeVar("T", bound="PackageAuditResult")


@_attrs_define
class PackageAuditResult:
    """
    Attributes:
        target (str):
        checks (list['AuditCheckResult']):
        fixes (list[str]):
        summary (Union[Unset, str]):  Default: ''.
    """

    target: str
    checks: list["AuditCheckResult"]
    fixes: list[str]
    summary: Union[Unset, str] = ""
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        target = self.target

        checks = []
        for checks_item_data in self.checks:
            checks_item = checks_item_data.to_dict()
            checks.append(checks_item)

        fixes = self.fixes

        summary = self.summary

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "target": target,
                "checks": checks,
                "fixes": fixes,
            }
        )
        if summary is not UNSET:
            field_dict["summary"] = summary

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.audit_check_result import AuditCheckResult

        d = dict(src_dict)
        target = d.pop("target")

        checks = []
        _checks = d.pop("checks")
        for checks_item_data in _checks:
            checks_item = AuditCheckResult.from_dict(checks_item_data)

            checks.append(checks_item)

        fixes = cast(list[str], d.pop("fixes"))

        summary = d.pop("summary", UNSET)

        package_audit_result = cls(
            target=target,
            checks=checks,
            fixes=fixes,
            summary=summary,
        )

        package_audit_result.additional_properties = d
        return package_audit_result

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
