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
    from ..models.analysis_config_options_multiseed import AnalysisConfigOptionsMultiseed
    from ..models.analysis_config_options_multiexperiment import AnalysisConfigOptionsMultiexperiment
    from ..models.analysis_config_options_single import AnalysisConfigOptionsSingle
    from ..models.analysis_config_options_multivariant import AnalysisConfigOptionsMultivariant
    from ..models.analysis_config_options_multigeneration import AnalysisConfigOptionsMultigeneration
    from ..models.analysis_config_options_multidaughter import AnalysisConfigOptionsMultidaughter


T = TypeVar("T", bound="AnalysisConfigOptions")


@_attrs_define
class AnalysisConfigOptions:
    """
    Attributes:
        experiment_id (list[str]):
        variant_data_dir (Union[None, Unset, list[str]]):
        validation_data_path (Union[None, Unset, list[str]]):
        outdir (Union[None, Unset, str]):
        cpus (Union[Unset, int]):  Default: 3.
        single (Union[Unset, AnalysisConfigOptionsSingle]):
        multidaughter (Union[Unset, AnalysisConfigOptionsMultidaughter]):
        multigeneration (Union[Unset, AnalysisConfigOptionsMultigeneration]):
        multiseed (Union[Unset, AnalysisConfigOptionsMultiseed]):
        multivariant (Union[Unset, AnalysisConfigOptionsMultivariant]):
        multiexperiment (Union[Unset, AnalysisConfigOptionsMultiexperiment]):
    """

    experiment_id: list[str]
    variant_data_dir: Union[None, Unset, list[str]] = UNSET
    validation_data_path: Union[None, Unset, list[str]] = UNSET
    outdir: Union[None, Unset, str] = UNSET
    cpus: Union[Unset, int] = 3
    single: Union[Unset, "AnalysisConfigOptionsSingle"] = UNSET
    multidaughter: Union[Unset, "AnalysisConfigOptionsMultidaughter"] = UNSET
    multigeneration: Union[Unset, "AnalysisConfigOptionsMultigeneration"] = UNSET
    multiseed: Union[Unset, "AnalysisConfigOptionsMultiseed"] = UNSET
    multivariant: Union[Unset, "AnalysisConfigOptionsMultivariant"] = UNSET
    multiexperiment: Union[Unset, "AnalysisConfigOptionsMultiexperiment"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.analysis_config_options_multiseed import AnalysisConfigOptionsMultiseed
        from ..models.analysis_config_options_multiexperiment import AnalysisConfigOptionsMultiexperiment
        from ..models.analysis_config_options_single import AnalysisConfigOptionsSingle
        from ..models.analysis_config_options_multivariant import AnalysisConfigOptionsMultivariant
        from ..models.analysis_config_options_multigeneration import AnalysisConfigOptionsMultigeneration
        from ..models.analysis_config_options_multidaughter import AnalysisConfigOptionsMultidaughter

        experiment_id = self.experiment_id

        variant_data_dir: Union[None, Unset, list[str]]
        if isinstance(self.variant_data_dir, Unset):
            variant_data_dir = UNSET
        elif isinstance(self.variant_data_dir, list):
            variant_data_dir = self.variant_data_dir

        else:
            variant_data_dir = self.variant_data_dir

        validation_data_path: Union[None, Unset, list[str]]
        if isinstance(self.validation_data_path, Unset):
            validation_data_path = UNSET
        elif isinstance(self.validation_data_path, list):
            validation_data_path = self.validation_data_path

        else:
            validation_data_path = self.validation_data_path

        outdir: Union[None, Unset, str]
        if isinstance(self.outdir, Unset):
            outdir = UNSET
        else:
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
        field_dict.update({
            "experiment_id": experiment_id,
        })
        if variant_data_dir is not UNSET:
            field_dict["variant_data_dir"] = variant_data_dir
        if validation_data_path is not UNSET:
            field_dict["validation_data_path"] = validation_data_path
        if outdir is not UNSET:
            field_dict["outdir"] = outdir
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
        from ..models.analysis_config_options_multiseed import AnalysisConfigOptionsMultiseed
        from ..models.analysis_config_options_multiexperiment import AnalysisConfigOptionsMultiexperiment
        from ..models.analysis_config_options_single import AnalysisConfigOptionsSingle
        from ..models.analysis_config_options_multivariant import AnalysisConfigOptionsMultivariant
        from ..models.analysis_config_options_multigeneration import AnalysisConfigOptionsMultigeneration
        from ..models.analysis_config_options_multidaughter import AnalysisConfigOptionsMultidaughter

        d = dict(src_dict)
        experiment_id = cast(list[str], d.pop("experiment_id"))

        def _parse_variant_data_dir(data: object) -> Union[None, Unset, list[str]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                variant_data_dir_type_0 = cast(list[str], data)

                return variant_data_dir_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[str]], data)

        variant_data_dir = _parse_variant_data_dir(d.pop("variant_data_dir", UNSET))

        def _parse_validation_data_path(data: object) -> Union[None, Unset, list[str]]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                validation_data_path_type_0 = cast(list[str], data)

                return validation_data_path_type_0
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[str]], data)

        validation_data_path = _parse_validation_data_path(d.pop("validation_data_path", UNSET))

        def _parse_outdir(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        outdir = _parse_outdir(d.pop("outdir", UNSET))

        cpus = d.pop("cpus", UNSET)

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
