from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import Union

if TYPE_CHECKING:
    from ..models.analysis_config_emitter_arg import AnalysisConfigEmitterArg
    from ..models.analysis_config_options import AnalysisConfigOptions


T = TypeVar("T", bound="AnalysisConfig")


@_attrs_define
class AnalysisConfig:
    """
    Attributes:
        analysis_options (AnalysisConfigOptions):
        emitter_arg (Union[Unset, AnalysisConfigEmitterArg]):
    """

    analysis_options: "AnalysisConfigOptions"
    emitter_arg: Union[Unset, "AnalysisConfigEmitterArg"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.analysis_config_emitter_arg import AnalysisConfigEmitterArg
        from ..models.analysis_config_options import AnalysisConfigOptions

        analysis_options = self.analysis_options.to_dict()

        emitter_arg: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.emitter_arg, Unset):
            emitter_arg = self.emitter_arg.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "analysis_options": analysis_options,
        })
        if emitter_arg is not UNSET:
            field_dict["emitter_arg"] = emitter_arg

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.analysis_config_emitter_arg import AnalysisConfigEmitterArg
        from ..models.analysis_config_options import AnalysisConfigOptions

        d = dict(src_dict)
        analysis_options = AnalysisConfigOptions.from_dict(d.pop("analysis_options"))

        _emitter_arg = d.pop("emitter_arg", UNSET)
        emitter_arg: Union[Unset, AnalysisConfigEmitterArg]
        if isinstance(_emitter_arg, Unset):
            emitter_arg = UNSET
        else:
            emitter_arg = AnalysisConfigEmitterArg.from_dict(_emitter_arg)

        analysis_config = cls(
            analysis_options=analysis_options,
            emitter_arg=emitter_arg,
        )

        analysis_config.additional_properties = d
        return analysis_config

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
