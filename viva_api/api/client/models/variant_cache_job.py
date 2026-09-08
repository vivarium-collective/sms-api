from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="VariantCacheJob")


@_attrs_define
class VariantCacheJob:
    """Response for a submitted variant-cache job. Same v1-scoped shape as
    ``NewGeneCacheJob`` -- no HpcRun/DB tracking, poll the returned ``job_id``
    directly against the compute backend.

        Attributes:
            job_id (str):
            commit (str):
            variant (str):
            cache_s3_uri (str):
    """

    job_id: str
    commit: str
    variant: str
    cache_s3_uri: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        job_id = self.job_id

        commit = self.commit

        variant = self.variant

        cache_s3_uri = self.cache_s3_uri

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "job_id": job_id,
            "commit": commit,
            "variant": variant,
            "cache_s3_uri": cache_s3_uri,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        job_id = d.pop("job_id")

        commit = d.pop("commit")

        variant = d.pop("variant")

        cache_s3_uri = d.pop("cache_s3_uri")

        variant_cache_job = cls(
            job_id=job_id,
            commit=commit,
            variant=variant,
            cache_s3_uri=cache_s3_uri,
        )

        variant_cache_job.additional_properties = d
        return variant_cache_job

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
