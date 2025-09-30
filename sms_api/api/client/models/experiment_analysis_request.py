from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import Union

if TYPE_CHECKING:
    from ..models.experiment_analysis_request_multigeneration import ExperimentAnalysisRequestMultigeneration
    from ..models.experiment_analysis_request_multiseed import ExperimentAnalysisRequestMultiseed
    from ..models.experiment_analysis_request_single import ExperimentAnalysisRequestSingle
    from ..models.experiment_analysis_request_multivariant import ExperimentAnalysisRequestMultivariant
    from ..models.experiment_analysis_request_multiexperiment import ExperimentAnalysisRequestMultiexperiment
    from ..models.experiment_analysis_request_multidaughter import ExperimentAnalysisRequestMultidaughter


T = TypeVar("T", bound="ExperimentAnalysisRequest")


@_attrs_define
class ExperimentAnalysisRequest:
    """
    Attributes:
        experiment_id (str):
        analysis_name (Union[Unset, str]):  Default: 'analysis_smsapi-103ea058fd342807_1759239346589'.
        single (Union[Unset, ExperimentAnalysisRequestSingle]):
        multidaughter (Union[Unset, ExperimentAnalysisRequestMultidaughter]):
        multigeneration (Union[Unset, ExperimentAnalysisRequestMultigeneration]):
        multiseed (Union[Unset, ExperimentAnalysisRequestMultiseed]):
        multivariant (Union[Unset, ExperimentAnalysisRequestMultivariant]):
        multiexperiment (Union[Unset, ExperimentAnalysisRequestMultiexperiment]):
    """

    experiment_id: str
    analysis_name: Union[Unset, str] = "analysis_smsapi-103ea058fd342807_1759239346589"
    single: Union[Unset, "ExperimentAnalysisRequestSingle"] = UNSET
    multidaughter: Union[Unset, "ExperimentAnalysisRequestMultidaughter"] = UNSET
    multigeneration: Union[Unset, "ExperimentAnalysisRequestMultigeneration"] = UNSET
    multiseed: Union[Unset, "ExperimentAnalysisRequestMultiseed"] = UNSET
    multivariant: Union[Unset, "ExperimentAnalysisRequestMultivariant"] = UNSET
    multiexperiment: Union[Unset, "ExperimentAnalysisRequestMultiexperiment"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.experiment_analysis_request_multigeneration import ExperimentAnalysisRequestMultigeneration
        from ..models.experiment_analysis_request_multiseed import ExperimentAnalysisRequestMultiseed
        from ..models.experiment_analysis_request_single import ExperimentAnalysisRequestSingle
        from ..models.experiment_analysis_request_multivariant import ExperimentAnalysisRequestMultivariant
        from ..models.experiment_analysis_request_multiexperiment import ExperimentAnalysisRequestMultiexperiment
        from ..models.experiment_analysis_request_multidaughter import ExperimentAnalysisRequestMultidaughter

        experiment_id = self.experiment_id

        analysis_name = self.analysis_name

        single: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.single, Unset):
            single = self.single.to_dict()

        multidaughter: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.multidaughter, Unset):
            multidaughter = self.multidaughter.to_dict()

        multigeneration: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.multigeneration, Unset):
            multigeneration = self.multigeneration.to_dict()

        multiseed: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.multiseed, Unset):
            multiseed = self.multiseed.to_dict()

        multivariant: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.multivariant, Unset):
            multivariant = self.multivariant.to_dict()

        multiexperiment: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.multiexperiment, Unset):
            multiexperiment = self.multiexperiment.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "experiment_id": experiment_id,
        })
        if analysis_name is not UNSET:
            field_dict["analysis_name"] = analysis_name
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
        from ..models.experiment_analysis_request_multigeneration import ExperimentAnalysisRequestMultigeneration
        from ..models.experiment_analysis_request_multiseed import ExperimentAnalysisRequestMultiseed
        from ..models.experiment_analysis_request_single import ExperimentAnalysisRequestSingle
        from ..models.experiment_analysis_request_multivariant import ExperimentAnalysisRequestMultivariant
        from ..models.experiment_analysis_request_multiexperiment import ExperimentAnalysisRequestMultiexperiment
        from ..models.experiment_analysis_request_multidaughter import ExperimentAnalysisRequestMultidaughter

        d = dict(src_dict)
        experiment_id = d.pop("experiment_id")

        analysis_name = d.pop("analysis_name", UNSET)

        _single = d.pop("single", UNSET)
        single: Union[Unset, ExperimentAnalysisRequestSingle]
        if isinstance(_single, Unset):
            single = UNSET
        else:
            single = ExperimentAnalysisRequestSingle.from_dict(_single)

        _multidaughter = d.pop("multidaughter", UNSET)
        multidaughter: Union[Unset, ExperimentAnalysisRequestMultidaughter]
        if isinstance(_multidaughter, Unset):
            multidaughter = UNSET
        else:
            multidaughter = ExperimentAnalysisRequestMultidaughter.from_dict(_multidaughter)

        _multigeneration = d.pop("multigeneration", UNSET)
        multigeneration: Union[Unset, ExperimentAnalysisRequestMultigeneration]
        if isinstance(_multigeneration, Unset):
            multigeneration = UNSET
        else:
            multigeneration = ExperimentAnalysisRequestMultigeneration.from_dict(_multigeneration)

        _multiseed = d.pop("multiseed", UNSET)
        multiseed: Union[Unset, ExperimentAnalysisRequestMultiseed]
        if isinstance(_multiseed, Unset):
            multiseed = UNSET
        else:
            multiseed = ExperimentAnalysisRequestMultiseed.from_dict(_multiseed)

        _multivariant = d.pop("multivariant", UNSET)
        multivariant: Union[Unset, ExperimentAnalysisRequestMultivariant]
        if isinstance(_multivariant, Unset):
            multivariant = UNSET
        else:
            multivariant = ExperimentAnalysisRequestMultivariant.from_dict(_multivariant)

        _multiexperiment = d.pop("multiexperiment", UNSET)
        multiexperiment: Union[Unset, ExperimentAnalysisRequestMultiexperiment]
        if isinstance(_multiexperiment, Unset):
            multiexperiment = UNSET
        else:
            multiexperiment = ExperimentAnalysisRequestMultiexperiment.from_dict(_multiexperiment)

        experiment_analysis_request = cls(
            experiment_id=experiment_id,
            analysis_name=analysis_name,
            single=single,
            multidaughter=multidaughter,
            multigeneration=multigeneration,
            multiseed=multiseed,
            multivariant=multivariant,
            multiexperiment=multiexperiment,
        )

        experiment_analysis_request.additional_properties = d
        return experiment_analysis_request

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
