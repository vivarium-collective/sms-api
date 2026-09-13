from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from .. import types
from ..types import UNSET, Unset

T = TypeVar("T", bound="BodyComposeRunSimulation")


@_attrs_define
class BodyComposeRunSimulation:
    """
    Attributes:
        uploaded_file (str):
        analysis_options (Union[None, Unset, str]):
    """

    uploaded_file: str
    analysis_options: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        uploaded_file = self.uploaded_file

        analysis_options: Union[None, Unset, str]
        if isinstance(self.analysis_options, Unset):
            analysis_options = UNSET
        else:
            analysis_options = self.analysis_options

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "uploaded_file": uploaded_file,
        })
        if analysis_options is not UNSET:
            field_dict["analysis_options"] = analysis_options

        return field_dict

    def to_multipart(self) -> types.RequestFiles:
        files: types.RequestFiles = []

        files.append(("uploaded_file", (None, str(self.uploaded_file).encode(), "text/plain")))

        if not isinstance(self.analysis_options, Unset):
            if isinstance(self.analysis_options, str):
                files.append(("analysis_options", (None, str(self.analysis_options).encode(), "text/plain")))
            else:
                files.append(("analysis_options", (None, str(self.analysis_options).encode(), "text/plain")))

        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))

        return files

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        uploaded_file = d.pop("uploaded_file")

        def _parse_analysis_options(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        analysis_options = _parse_analysis_options(d.pop("analysis_options", UNSET))

        body_compose_run_simulation = cls(
            uploaded_file=uploaded_file,
            analysis_options=analysis_options,
        )

        body_compose_run_simulation.additional_properties = d
        return body_compose_run_simulation

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
