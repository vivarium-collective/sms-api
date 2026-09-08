from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define

from ..types import UNSET, Unset

T = TypeVar("T", bound="ParcaOptions")


@_attrs_define
class ParcaOptions:
    """
    Attributes:
        cpus (Union[None, Unset, int]):
        outdir (Union[Unset, str]):  Default: '/projects/SMS/sms_api/prod/sims'.
        operons (Union[Unset, bool]):  Default: True.
        ribosome_fitting (Union[Unset, bool]):  Default: True.
        rnapoly_fitting (Union[Unset, bool]):  Default: True.
        remove_rrna_operons (Union[Unset, bool]):  Default: False.
        remove_rrff (Union[Unset, bool]):  Default: False.
        stable_rrna (Union[Unset, bool]):  Default: False.
        new_genes (Union[Unset, str]):  Default: 'off'.
        bundle_overrides (Union[None, Unset, list[str], str]):
        rnaseq_source (Union[None, Unset, str]):
        require_clean_chain (Union[Unset, bool]):  Default: False.
        bundle_manifest_path (Union[None, Unset, str]):
        build_combined_bundle_manifest (Union[Unset, bool]):  Default: False.
        include_violacein_bundle (Union[Unset, bool]):  Default: False.
        deterministic_hash_seed (Union[Unset, bool]):  Default: False.
        debug_parca (Union[Unset, bool]):  Default: False.
        load_intermediate (Union[None, Unset, str]):
        save_intermediates (Union[Unset, bool]):  Default: False.
        intermediates_directory (Union[Unset, str]):  Default: ''.
        variable_elongation_transcription (Union[Unset, bool]):  Default: True.
        variable_elongation_translation (Union[Unset, bool]):  Default: False.
        include_violacein_reactions (Union[None, Unset, bool]):
    """

    cpus: Union[None, Unset, int] = UNSET
    outdir: Union[Unset, str] = "/projects/SMS/sms_api/prod/sims"
    operons: Union[Unset, bool] = True
    ribosome_fitting: Union[Unset, bool] = True
    rnapoly_fitting: Union[Unset, bool] = True
    remove_rrna_operons: Union[Unset, bool] = False
    remove_rrff: Union[Unset, bool] = False
    stable_rrna: Union[Unset, bool] = False
    new_genes: Union[Unset, str] = "off"
    bundle_overrides: Union[None, Unset, list[str], str] = UNSET
    rnaseq_source: Union[None, Unset, str] = UNSET
    require_clean_chain: Union[Unset, bool] = False
    bundle_manifest_path: Union[None, Unset, str] = UNSET
    build_combined_bundle_manifest: Union[Unset, bool] = False
    include_violacein_bundle: Union[Unset, bool] = False
    deterministic_hash_seed: Union[Unset, bool] = False
    debug_parca: Union[Unset, bool] = False
    load_intermediate: Union[None, Unset, str] = UNSET
    save_intermediates: Union[Unset, bool] = False
    intermediates_directory: Union[Unset, str] = ""
    variable_elongation_transcription: Union[Unset, bool] = True
    variable_elongation_translation: Union[Unset, bool] = False
    include_violacein_reactions: Union[None, Unset, bool] = UNSET

    def to_dict(self) -> dict[str, Any]:
        cpus: Union[None, Unset, int]
        if isinstance(self.cpus, Unset):
            cpus = UNSET
        else:
            cpus = self.cpus

        outdir = self.outdir

        operons = self.operons

        ribosome_fitting = self.ribosome_fitting

        rnapoly_fitting = self.rnapoly_fitting

        remove_rrna_operons = self.remove_rrna_operons

        remove_rrff = self.remove_rrff

        stable_rrna = self.stable_rrna

        new_genes = self.new_genes

        bundle_overrides: Union[None, Unset, list[str], str]
        if isinstance(self.bundle_overrides, Unset):
            bundle_overrides = UNSET
        elif isinstance(self.bundle_overrides, list):
            bundle_overrides = self.bundle_overrides

        else:
            bundle_overrides = self.bundle_overrides

        rnaseq_source: Union[None, Unset, str]
        if isinstance(self.rnaseq_source, Unset):
            rnaseq_source = UNSET
        else:
            rnaseq_source = self.rnaseq_source

        require_clean_chain = self.require_clean_chain

        bundle_manifest_path: Union[None, Unset, str]
        if isinstance(self.bundle_manifest_path, Unset):
            bundle_manifest_path = UNSET
        else:
            bundle_manifest_path = self.bundle_manifest_path

        build_combined_bundle_manifest = self.build_combined_bundle_manifest

        include_violacein_bundle = self.include_violacein_bundle

        deterministic_hash_seed = self.deterministic_hash_seed

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

        include_violacein_reactions: Union[None, Unset, bool]
        if isinstance(self.include_violacein_reactions, Unset):
            include_violacein_reactions = UNSET
        else:
            include_violacein_reactions = self.include_violacein_reactions

        field_dict: dict[str, Any] = {}

        field_dict.update({})
        if cpus is not UNSET:
            field_dict["cpus"] = cpus
        if outdir is not UNSET:
            field_dict["outdir"] = outdir
        if operons is not UNSET:
            field_dict["operons"] = operons
        if ribosome_fitting is not UNSET:
            field_dict["ribosome_fitting"] = ribosome_fitting
        if rnapoly_fitting is not UNSET:
            field_dict["rnapoly_fitting"] = rnapoly_fitting
        if remove_rrna_operons is not UNSET:
            field_dict["remove_rrna_operons"] = remove_rrna_operons
        if remove_rrff is not UNSET:
            field_dict["remove_rrff"] = remove_rrff
        if stable_rrna is not UNSET:
            field_dict["stable_rrna"] = stable_rrna
        if new_genes is not UNSET:
            field_dict["new_genes"] = new_genes
        if bundle_overrides is not UNSET:
            field_dict["bundle_overrides"] = bundle_overrides
        if rnaseq_source is not UNSET:
            field_dict["rnaseq_source"] = rnaseq_source
        if require_clean_chain is not UNSET:
            field_dict["require_clean_chain"] = require_clean_chain
        if bundle_manifest_path is not UNSET:
            field_dict["bundle_manifest_path"] = bundle_manifest_path
        if build_combined_bundle_manifest is not UNSET:
            field_dict["build_combined_bundle_manifest"] = build_combined_bundle_manifest
        if include_violacein_bundle is not UNSET:
            field_dict["include_violacein_bundle"] = include_violacein_bundle
        if deterministic_hash_seed is not UNSET:
            field_dict["deterministic_hash_seed"] = deterministic_hash_seed
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
        if include_violacein_reactions is not UNSET:
            field_dict["include_violacein_reactions"] = include_violacein_reactions

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)

        def _parse_cpus(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        cpus = _parse_cpus(d.pop("cpus", UNSET))

        outdir = d.pop("outdir", UNSET)

        operons = d.pop("operons", UNSET)

        ribosome_fitting = d.pop("ribosome_fitting", UNSET)

        rnapoly_fitting = d.pop("rnapoly_fitting", UNSET)

        remove_rrna_operons = d.pop("remove_rrna_operons", UNSET)

        remove_rrff = d.pop("remove_rrff", UNSET)

        stable_rrna = d.pop("stable_rrna", UNSET)

        new_genes = d.pop("new_genes", UNSET)

        def _parse_bundle_overrides(data: object) -> Union[None, Unset, list[str], str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                bundle_overrides_type_1 = cast(list[str], data)

                return bundle_overrides_type_1
            except:  # noqa: E722
                pass
            return cast(Union[None, Unset, list[str], str], data)

        bundle_overrides = _parse_bundle_overrides(d.pop("bundle_overrides", UNSET))

        def _parse_rnaseq_source(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        rnaseq_source = _parse_rnaseq_source(d.pop("rnaseq_source", UNSET))

        require_clean_chain = d.pop("require_clean_chain", UNSET)

        def _parse_bundle_manifest_path(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        bundle_manifest_path = _parse_bundle_manifest_path(d.pop("bundle_manifest_path", UNSET))

        build_combined_bundle_manifest = d.pop("build_combined_bundle_manifest", UNSET)

        include_violacein_bundle = d.pop("include_violacein_bundle", UNSET)

        deterministic_hash_seed = d.pop("deterministic_hash_seed", UNSET)

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

        def _parse_include_violacein_reactions(data: object) -> Union[None, Unset, bool]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, bool], data)

        include_violacein_reactions = _parse_include_violacein_reactions(d.pop("include_violacein_reactions", UNSET))

        parca_options = cls(
            cpus=cpus,
            outdir=outdir,
            operons=operons,
            ribosome_fitting=ribosome_fitting,
            rnapoly_fitting=rnapoly_fitting,
            remove_rrna_operons=remove_rrna_operons,
            remove_rrff=remove_rrff,
            stable_rrna=stable_rrna,
            new_genes=new_genes,
            bundle_overrides=bundle_overrides,
            rnaseq_source=rnaseq_source,
            require_clean_chain=require_clean_chain,
            bundle_manifest_path=bundle_manifest_path,
            build_combined_bundle_manifest=build_combined_bundle_manifest,
            include_violacein_bundle=include_violacein_bundle,
            deterministic_hash_seed=deterministic_hash_seed,
            debug_parca=debug_parca,
            load_intermediate=load_intermediate,
            save_intermediates=save_intermediates,
            intermediates_directory=intermediates_directory,
            variable_elongation_transcription=variable_elongation_transcription,
            variable_elongation_translation=variable_elongation_translation,
            include_violacein_reactions=include_violacein_reactions,
        )

        return parca_options
