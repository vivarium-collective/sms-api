from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.variant_cache_request_perturbations import VariantCacheRequestPerturbations


T = TypeVar("T", bound="VariantCacheRequest")


@_attrs_define
class VariantCacheRequest:
    """Backlog item 451: stamp NATIVE-gene translation-efficiency perturbations
    onto a COMPLETED ParCa dataset's cache (``scripts/build_variant_cache.py``,
    the sibling mechanism to ``NewGeneCacheRequest`` above -- native-gene
    knockouts/knockdowns/overexpression instead of a new gene's own induction
    level -- see ``SimulationServiceRay.submit_variant_cache_job``). Ray/Batch
    backend only; the source dataset must already have SUCCEEDED (not
    re-validated here, same pure-passthrough philosophy as
    ``NewGeneCacheRequest``).

        Attributes:
            parca_dataset_id (int):
            variant (str):
            perturbations (VariantCacheRequestPerturbations):
            seed (Union[Unset, int]):  Default: 0.
            fixed_media (Union[None, Unset, str]):
    """

    parca_dataset_id: int
    variant: str
    perturbations: "VariantCacheRequestPerturbations"
    seed: Union[Unset, int] = 0
    fixed_media: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        parca_dataset_id = self.parca_dataset_id

        variant = self.variant

        perturbations = self.perturbations.to_dict()

        seed = self.seed

        fixed_media: Union[None, Unset, str]
        if isinstance(self.fixed_media, Unset):
            fixed_media = UNSET
        else:
            fixed_media = self.fixed_media

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "parca_dataset_id": parca_dataset_id,
                "variant": variant,
                "perturbations": perturbations,
            }
        )
        if seed is not UNSET:
            field_dict["seed"] = seed
        if fixed_media is not UNSET:
            field_dict["fixed_media"] = fixed_media

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.variant_cache_request_perturbations import VariantCacheRequestPerturbations

        d = dict(src_dict)
        parca_dataset_id = d.pop("parca_dataset_id")

        variant = d.pop("variant")

        perturbations = VariantCacheRequestPerturbations.from_dict(d.pop("perturbations"))

        seed = d.pop("seed", UNSET)

        def _parse_fixed_media(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        fixed_media = _parse_fixed_media(d.pop("fixed_media", UNSET))

        variant_cache_request = cls(
            parca_dataset_id=parca_dataset_id,
            variant=variant,
            perturbations=perturbations,
            seed=seed,
            fixed_media=fixed_media,
        )

        variant_cache_request.additional_properties = d
        return variant_cache_request

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
