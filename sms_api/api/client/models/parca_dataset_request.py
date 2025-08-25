from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
    from ..models.parca_dataset_request_parca_config import ParcaDatasetRequestParcaConfig
    from ..models.simulator_version import SimulatorVersion


T = TypeVar("T", bound="ParcaDatasetRequest")


@_attrs_define
class ParcaDatasetRequest:
    """
    Attributes:
        simulator_version (SimulatorVersion):
        parca_config (ParcaDatasetRequestParcaConfig):
    """

    simulator_version: "SimulatorVersion"
    parca_config: "ParcaDatasetRequestParcaConfig"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.parca_dataset_request_parca_config import ParcaDatasetRequestParcaConfig
        from ..models.simulator_version import SimulatorVersion

        simulator_version = self.simulator_version.to_dict()

        parca_config = self.parca_config.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "simulator_version": simulator_version,
            "parca_config": parca_config,
        })

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.parca_dataset_request_parca_config import ParcaDatasetRequestParcaConfig
        from ..models.simulator_version import SimulatorVersion

        d = dict(src_dict)
        simulator_version = SimulatorVersion.from_dict(d.pop("simulator_version"))

        parca_config = ParcaDatasetRequestParcaConfig.from_dict(d.pop("parca_config"))

        parca_dataset_request = cls(
            simulator_version=simulator_version,
            parca_config=parca_config,
        )

        parca_dataset_request.additional_properties = d
        return parca_dataset_request

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
