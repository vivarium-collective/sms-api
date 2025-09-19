from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.analysis_config_options_multidaughter import AnalysisConfigOptionsMultidaughter
    from ..models.analysis_config_options_multiexperiment import AnalysisConfigOptionsMultiexperiment
    from ..models.analysis_config_options_multigeneration import AnalysisConfigOptionsMultigeneration
    from ..models.analysis_config_options_multiseed import AnalysisConfigOptionsMultiseed
    from ..models.analysis_config_options_multivariant import AnalysisConfigOptionsMultivariant
    from ..models.analysis_config_options_single import AnalysisConfigOptionsSingle


T = TypeVar("T", bound="AnalysisConfigOptions")


@_attrs_define
class AnalysisConfigOptions:
    """
    Attributes:
        experiment_id (list[str]):
        variant_data_dir (list[str]):
        validation_data_path (list[str]):
        outdir (str):
        cpus (int):
        single (Union[Unset, AnalysisConfigOptionsSingle]):
        multidaughter (Union[Unset, AnalysisConfigOptionsMultidaughter]):
        multigeneration (Union[Unset, AnalysisConfigOptionsMultigeneration]):
        multiseed (Union[Unset, AnalysisConfigOptionsMultiseed]):
        multivariant (Union[Unset, AnalysisConfigOptionsMultivariant]):
        multiexperiment (Union[Unset, AnalysisConfigOptionsMultiexperiment]):
    """

    experiment_id: list[str]
    variant_data_dir: list[str]
    validation_data_path: list[str]
    outdir: str
    cpus: int
    single: Union[Unset, "AnalysisConfigOptionsSingle"] = UNSET
    multidaughter: Union[Unset, "AnalysisConfigOptionsMultidaughter"] = UNSET
    multigeneration: Union[Unset, "AnalysisConfigOptionsMultigeneration"] = UNSET
    multiseed: Union[Unset, "AnalysisConfigOptionsMultiseed"] = UNSET
    multivariant: Union[Unset, "AnalysisConfigOptionsMultivariant"] = UNSET
    multiexperiment: Union[Unset, "AnalysisConfigOptionsMultiexperiment"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        experiment_id = self.experiment_id

        variant_data_dir = self.variant_data_dir

        validation_data_path = self.validation_data_path

        outdir = self.outdir

        cpus = self.cpus

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
        field_dict.update(
            {
                "experiment_id": experiment_id,
                "variant_data_dir": variant_data_dir,
                "validation_data_path": validation_data_path,
                "outdir": outdir,
                "cpus": cpus,
            }
        )
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
        from ..models.analysis_config_options_multidaughter import AnalysisConfigOptionsMultidaughter
        from ..models.analysis_config_options_multiexperiment import AnalysisConfigOptionsMultiexperiment
        from ..models.analysis_config_options_multigeneration import AnalysisConfigOptionsMultigeneration
        from ..models.analysis_config_options_multiseed import AnalysisConfigOptionsMultiseed
        from ..models.analysis_config_options_multivariant import AnalysisConfigOptionsMultivariant
        from ..models.analysis_config_options_single import AnalysisConfigOptionsSingle

        d = dict(src_dict)
        experiment_id = cast(list[str], d.pop("experiment_id"))

        variant_data_dir = cast(list[str], d.pop("variant_data_dir"))

        validation_data_path = cast(list[str], d.pop("validation_data_path"))

        outdir = d.pop("outdir")

        cpus = d.pop("cpus")

        _single = d.pop("single", UNSET)
        single: Union[Unset, AnalysisConfigOptionsSingle]
        if isinstance(_single, Unset):
            single = UNSET
        else:
            single = AnalysisConfigOptionsSingle.from_dict(_single)

        _multidaughter = d.pop("multidaughter", UNSET)
        multidaughter: Union[Unset, AnalysisConfigOptionsMultidaughter]
        if isinstance(_multidaughter, Unset):
            multidaughter = UNSET
        else:
            multidaughter = AnalysisConfigOptionsMultidaughter.from_dict(_multidaughter)

        _multigeneration = d.pop("multigeneration", UNSET)
        multigeneration: Union[Unset, AnalysisConfigOptionsMultigeneration]
        if isinstance(_multigeneration, Unset):
            multigeneration = UNSET
        else:
            multigeneration = AnalysisConfigOptionsMultigeneration.from_dict(_multigeneration)

        _multiseed = d.pop("multiseed", UNSET)
        multiseed: Union[Unset, AnalysisConfigOptionsMultiseed]
        if isinstance(_multiseed, Unset):
            multiseed = UNSET
        else:
            multiseed = AnalysisConfigOptionsMultiseed.from_dict(_multiseed)

        _multivariant = d.pop("multivariant", UNSET)
        multivariant: Union[Unset, AnalysisConfigOptionsMultivariant]
        if isinstance(_multivariant, Unset):
            multivariant = UNSET
        else:
            multivariant = AnalysisConfigOptionsMultivariant.from_dict(_multivariant)

        _multiexperiment = d.pop("multiexperiment", UNSET)
        multiexperiment: Union[Unset, AnalysisConfigOptionsMultiexperiment]
        if isinstance(_multiexperiment, Unset):
            multiexperiment = UNSET
        else:
            multiexperiment = AnalysisConfigOptionsMultiexperiment.from_dict(_multiexperiment)

        analysis_config_options = cls(
            experiment_id=experiment_id,
            variant_data_dir=variant_data_dir,
            validation_data_path=validation_data_path,
            outdir=outdir,
            cpus=cpus,
            single=single,
            multidaughter=multidaughter,
            multigeneration=multigeneration,
            multiseed=multiseed,
            multivariant=multivariant,
            multiexperiment=multiexperiment,
        )

        analysis_config_options.additional_properties = d
        return analysis_config_options

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
