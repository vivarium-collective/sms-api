from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.analysis_options_multidaughter_type_0 import AnalysisOptionsMultidaughterType0
    from ..models.analysis_options_multiexperiment_type_0 import AnalysisOptionsMultiexperimentType0
    from ..models.analysis_options_multigeneration_type_0 import AnalysisOptionsMultigenerationType0
    from ..models.analysis_options_multiseed_type_0 import AnalysisOptionsMultiseedType0
    from ..models.analysis_options_multivariant_type_0 import AnalysisOptionsMultivariantType0
    from ..models.analysis_options_single_type_0 import AnalysisOptionsSingleType0


T = TypeVar("T", bound="AnalysisOptions")


@_attrs_define
class AnalysisOptions:
    """
    Attributes:
        cpus (Union[Unset, int]):  Default: 3.
        single (Union['AnalysisOptionsSingleType0', None, Unset]):
        multidaughter (Union['AnalysisOptionsMultidaughterType0', None, Unset]):
        multigeneration (Union['AnalysisOptionsMultigenerationType0', None, Unset]):
        multiseed (Union['AnalysisOptionsMultiseedType0', None, Unset]):
        multivariant (Union['AnalysisOptionsMultivariantType0', None, Unset]):
        multiexperiment (Union['AnalysisOptionsMultiexperimentType0', None, Unset]):
    """

    cpus: Union[Unset, int] = 3
    single: Union["AnalysisOptionsSingleType0", None, Unset] = UNSET
    multidaughter: Union["AnalysisOptionsMultidaughterType0", None, Unset] = UNSET
    multigeneration: Union["AnalysisOptionsMultigenerationType0", None, Unset] = UNSET
    multiseed: Union["AnalysisOptionsMultiseedType0", None, Unset] = UNSET
    multivariant: Union["AnalysisOptionsMultivariantType0", None, Unset] = UNSET
    multiexperiment: Union["AnalysisOptionsMultiexperimentType0", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.analysis_options_multidaughter_type_0 import AnalysisOptionsMultidaughterType0
        from ..models.analysis_options_multiexperiment_type_0 import AnalysisOptionsMultiexperimentType0
        from ..models.analysis_options_multigeneration_type_0 import AnalysisOptionsMultigenerationType0
        from ..models.analysis_options_multiseed_type_0 import AnalysisOptionsMultiseedType0
        from ..models.analysis_options_multivariant_type_0 import AnalysisOptionsMultivariantType0
        from ..models.analysis_options_single_type_0 import AnalysisOptionsSingleType0

        cpus = self.cpus

        single: Union[None, Unset, dict[str, Any]]
        if isinstance(self.single, Unset):
            single = UNSET
        elif isinstance(self.single, AnalysisOptionsSingleType0):
            single = self.single.to_dict()
        else:
            single = self.single

        multidaughter: Union[None, Unset, dict[str, Any]]
        if isinstance(self.multidaughter, Unset):
            multidaughter = UNSET
        elif isinstance(self.multidaughter, AnalysisOptionsMultidaughterType0):
            multidaughter = self.multidaughter.to_dict()
        else:
            multidaughter = self.multidaughter

        multigeneration: Union[None, Unset, dict[str, Any]]
        if isinstance(self.multigeneration, Unset):
            multigeneration = UNSET
        elif isinstance(self.multigeneration, AnalysisOptionsMultigenerationType0):
            multigeneration = self.multigeneration.to_dict()
        else:
            multigeneration = self.multigeneration

        multiseed: Union[None, Unset, dict[str, Any]]
        if isinstance(self.multiseed, Unset):
            multiseed = UNSET
        elif isinstance(self.multiseed, AnalysisOptionsMultiseedType0):
            multiseed = self.multiseed.to_dict()
        else:
            multiseed = self.multiseed

        multivariant: Union[None, Unset, dict[str, Any]]
        if isinstance(self.multivariant, Unset):
            multivariant = UNSET
        elif isinstance(self.multivariant, AnalysisOptionsMultivariantType0):
            multivariant = self.multivariant.to_dict()
        else:
            multivariant = self.multivariant

        multiexperiment: Union[None, Unset, dict[str, Any]]
        if isinstance(self.multiexperiment, Unset):
            multiexperiment = UNSET
        elif isinstance(self.multiexperiment, AnalysisOptionsMultiexperimentType0):
            multiexperiment = self.multiexperiment.to_dict()
        else:
            multiexperiment = self.multiexperiment

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if cpus is not UNSET:
            field_dict["cpus"] = cpus
        if single is not UNSET:
            field_dict["single"] = single
        if multidaughter is not UNSET:
            field_dict["multidaughter"] = multidaughter
        if multigeneration is not UNSET:
            field_dict["multigeneration"] = multigeneration
        if multiseed is not UNSET:
            field_dict["multiseed"] = multiseed
        if multivariant is not UNSET:
            field_dict["multivariant"] = multivariant
        if multiexperiment is not UNSET:
            field_dict["multiexperiment"] = multiexperiment

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.analysis_options_multidaughter_type_0 import AnalysisOptionsMultidaughterType0
        from ..models.analysis_options_multiexperiment_type_0 import AnalysisOptionsMultiexperimentType0
        from ..models.analysis_options_multigeneration_type_0 import AnalysisOptionsMultigenerationType0
        from ..models.analysis_options_multiseed_type_0 import AnalysisOptionsMultiseedType0
        from ..models.analysis_options_multivariant_type_0 import AnalysisOptionsMultivariantType0
        from ..models.analysis_options_single_type_0 import AnalysisOptionsSingleType0

        d = dict(src_dict)
        cpus = d.pop("cpus", UNSET)

        def _parse_single(data: object) -> Union["AnalysisOptionsSingleType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                single_type_0 = AnalysisOptionsSingleType0.from_dict(data)

                return single_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AnalysisOptionsSingleType0", None, Unset], data)

        single = _parse_single(d.pop("single", UNSET))

        def _parse_multidaughter(data: object) -> Union["AnalysisOptionsMultidaughterType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                multidaughter_type_0 = AnalysisOptionsMultidaughterType0.from_dict(data)

                return multidaughter_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AnalysisOptionsMultidaughterType0", None, Unset], data)

        multidaughter = _parse_multidaughter(d.pop("multidaughter", UNSET))

        def _parse_multigeneration(data: object) -> Union["AnalysisOptionsMultigenerationType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                multigeneration_type_0 = AnalysisOptionsMultigenerationType0.from_dict(data)

                return multigeneration_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AnalysisOptionsMultigenerationType0", None, Unset], data)

        multigeneration = _parse_multigeneration(d.pop("multigeneration", UNSET))

        def _parse_multiseed(data: object) -> Union["AnalysisOptionsMultiseedType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                multiseed_type_0 = AnalysisOptionsMultiseedType0.from_dict(data)

                return multiseed_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AnalysisOptionsMultiseedType0", None, Unset], data)

        multiseed = _parse_multiseed(d.pop("multiseed", UNSET))

        def _parse_multivariant(data: object) -> Union["AnalysisOptionsMultivariantType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                multivariant_type_0 = AnalysisOptionsMultivariantType0.from_dict(data)

                return multivariant_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AnalysisOptionsMultivariantType0", None, Unset], data)

        multivariant = _parse_multivariant(d.pop("multivariant", UNSET))

        def _parse_multiexperiment(data: object) -> Union["AnalysisOptionsMultiexperimentType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                multiexperiment_type_0 = AnalysisOptionsMultiexperimentType0.from_dict(data)

                return multiexperiment_type_0
            except:  # noqa: E722
                pass
            return cast(Union["AnalysisOptionsMultiexperimentType0", None, Unset], data)

        multiexperiment = _parse_multiexperiment(d.pop("multiexperiment", UNSET))

        analysis_options = cls(
            cpus=cpus,
            single=single,
            multidaughter=multidaughter,
            multigeneration=multigeneration,
            multiseed=multiseed,
            multivariant=multivariant,
            multiexperiment=multiexperiment,
        )

        analysis_options.additional_properties = d
        return analysis_options

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
