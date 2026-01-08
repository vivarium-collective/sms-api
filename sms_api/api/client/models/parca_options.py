from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="ParcaOptions")


@_attrs_define
class ParcaOptions:
    """
    Attributes:
        cpus (int):
        outdir (str):
        operons (Union[Unset, bool]):  Default: True.
        ribosome_fitting (Union[Unset, bool]):  Default: True.
        remove_rrna_operons (Union[Unset, bool]):  Default: False.
        remove_rrff (Union[Unset, bool]):  Default: False.
        stable_rrna (Union[Unset, bool]):  Default: False.
        new_genes (Union[Unset, str]):  Default: 'off'.
        debug_parca (Union[Unset, bool]):  Default: False.
        load_intermediate (Union[None, Unset, str]):
        save_intermediates (Union[Unset, bool]):  Default: False.
        intermediates_directory (Union[Unset, str]):  Default: ''.
        variable_elongation_transcription (Union[Unset, bool]):  Default: True.
        variable_elongation_translation (Union[Unset, bool]):  Default: False.
    """

    cpus: int
    outdir: str
    operons: Union[Unset, bool] = True
    ribosome_fitting: Union[Unset, bool] = True
    remove_rrna_operons: Union[Unset, bool] = False
    remove_rrff: Union[Unset, bool] = False
    stable_rrna: Union[Unset, bool] = False
    new_genes: Union[Unset, str] = "off"
    debug_parca: Union[Unset, bool] = False
    load_intermediate: Union[None, Unset, str] = UNSET
    save_intermediates: Union[Unset, bool] = False
    intermediates_directory: Union[Unset, str] = ""
    variable_elongation_transcription: Union[Unset, bool] = True
    variable_elongation_translation: Union[Unset, bool] = False
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        cpus = self.cpus

        outdir = self.outdir

        operons = self.operons

        ribosome_fitting = self.ribosome_fitting

        remove_rrna_operons = self.remove_rrna_operons

        remove_rrff = self.remove_rrff

        stable_rrna = self.stable_rrna

        new_genes = self.new_genes

        debug_parca = self.debug_parca

        load_intermediate: Union[None, Unset, str]
        if isinstance(self.load_intermediate, Unset):
            load_intermediate = UNSET
        else:
            load_intermediate = self.load_intermediate

        save_intermediates = self.save_intermediates

        intermediates_directory = self.intermediates_directory

        variable_elongation_transcription = self.variable_elongation_transcription

        variable_elongation_translation = self.variable_elongation_translation

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "cpus": cpus,
                "outdir": outdir,
            }
        )
        if operons is not UNSET:
            field_dict["operons"] = operons
        if ribosome_fitting is not UNSET:
            field_dict["ribosome_fitting"] = ribosome_fitting
        if remove_rrna_operons is not UNSET:
            field_dict["remove_rrna_operons"] = remove_rrna_operons
        if remove_rrff is not UNSET:
            field_dict["remove_rrff"] = remove_rrff
        if stable_rrna is not UNSET:
            field_dict["stable_rrna"] = stable_rrna
        if new_genes is not UNSET:
            field_dict["new_genes"] = new_genes
        if debug_parca is not UNSET:
            field_dict["debug_parca"] = debug_parca
        if load_intermediate is not UNSET:
            field_dict["load_intermediate"] = load_intermediate
        if save_intermediates is not UNSET:
            field_dict["save_intermediates"] = save_intermediates
        if intermediates_directory is not UNSET:
            field_dict["intermediates_directory"] = intermediates_directory
        if variable_elongation_transcription is not UNSET:
            field_dict["variable_elongation_transcription"] = variable_elongation_transcription
        if variable_elongation_translation is not UNSET:
            field_dict["variable_elongation_translation"] = variable_elongation_translation

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        cpus = d.pop("cpus")

        outdir = d.pop("outdir")

        operons = d.pop("operons", UNSET)

        ribosome_fitting = d.pop("ribosome_fitting", UNSET)

        remove_rrna_operons = d.pop("remove_rrna_operons", UNSET)

        remove_rrff = d.pop("remove_rrff", UNSET)

        stable_rrna = d.pop("stable_rrna", UNSET)

        new_genes = d.pop("new_genes", UNSET)

        debug_parca = d.pop("debug_parca", UNSET)

        def _parse_load_intermediate(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        load_intermediate = _parse_load_intermediate(d.pop("load_intermediate", UNSET))

        save_intermediates = d.pop("save_intermediates", UNSET)

        intermediates_directory = d.pop("intermediates_directory", UNSET)

        variable_elongation_transcription = d.pop("variable_elongation_transcription", UNSET)

        variable_elongation_translation = d.pop("variable_elongation_translation", UNSET)

        parca_options = cls(
            cpus=cpus,
            outdir=outdir,
            operons=operons,
            ribosome_fitting=ribosome_fitting,
            remove_rrna_operons=remove_rrna_operons,
            remove_rrff=remove_rrff,
            stable_rrna=stable_rrna,
            new_genes=new_genes,
            debug_parca=debug_parca,
            load_intermediate=load_intermediate,
            save_intermediates=save_intermediates,
            intermediates_directory=intermediates_directory,
            variable_elongation_transcription=variable_elongation_transcription,
            variable_elongation_translation=variable_elongation_translation,
        )

        parca_options.additional_properties = d
        return parca_options

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
