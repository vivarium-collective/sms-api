from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.body_run_experiment_metadata_type_0 import BodyRunExperimentMetadataType0
    from ..models.config_overrides import ConfigOverrides


T = TypeVar("T", bound="BodyRunExperiment")


@_attrs_define
class BodyRunExperiment:
    """
    Attributes:
        overrides (Union['ConfigOverrides', None, Unset]):
        metadata (Union['BodyRunExperimentMetadataType0', None, Unset]):
    """

    overrides: Union["ConfigOverrides", None, Unset] = UNSET
    metadata: Union["BodyRunExperimentMetadataType0", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.body_run_experiment_metadata_type_0 import BodyRunExperimentMetadataType0
        from ..models.config_overrides import ConfigOverrides

        overrides: Union[None, Unset, dict[str, Any]]
        if isinstance(self.overrides, Unset):
            overrides = UNSET
        elif isinstance(self.overrides, ConfigOverrides):
            overrides = self.overrides.to_dict()
        else:
            overrides = self.overrides

        metadata: Union[None, Unset, dict[str, Any]]
        if isinstance(self.metadata, Unset):
            metadata = UNSET
        elif isinstance(self.metadata, BodyRunExperimentMetadataType0):
            metadata = self.metadata.to_dict()
        else:
            metadata = self.metadata

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if overrides is not UNSET:
            field_dict["overrides"] = overrides
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.body_run_experiment_metadata_type_0 import BodyRunExperimentMetadataType0
        from ..models.config_overrides import ConfigOverrides

        d = dict(src_dict)

        def _parse_overrides(data: object) -> Union["ConfigOverrides", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                overrides_type_0 = ConfigOverrides.from_dict(data)

                return overrides_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ConfigOverrides", None, Unset], data)

        overrides = _parse_overrides(d.pop("overrides", UNSET))

        def _parse_metadata(data: object) -> Union["BodyRunExperimentMetadataType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                metadata_type_0 = BodyRunExperimentMetadataType0.from_dict(data)

                return metadata_type_0
            except:  # noqa: E722
                pass
            return cast(Union["BodyRunExperimentMetadataType0", None, Unset], data)

        metadata = _parse_metadata(d.pop("metadata", UNSET))

        body_run_experiment = cls(
            overrides=overrides,
            metadata=metadata,
        )

        body_run_experiment.additional_properties = d
        return body_run_experiment

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
