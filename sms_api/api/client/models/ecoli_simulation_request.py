from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import Union

if TYPE_CHECKING:
    from ..models.ecoli_simulation_request_variant_config import EcoliSimulationRequestVariantConfig
    from ..models.simulator_version import SimulatorVersion


T = TypeVar("T", bound="EcoliSimulationRequest")


@_attrs_define
class EcoliSimulationRequest:
    """Fits EcoliSim

    Attributes:
        simulator (SimulatorVersion):
        parca_dataset_id (int):
        variant_config (Union[Unset, EcoliSimulationRequestVariantConfig]):
    """

    simulator: "SimulatorVersion"
    parca_dataset_id: int
    variant_config: Union[Unset, "EcoliSimulationRequestVariantConfig"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.ecoli_simulation_request_variant_config import EcoliSimulationRequestVariantConfig
        from ..models.simulator_version import SimulatorVersion

        simulator = self.simulator.to_dict()

        parca_dataset_id = self.parca_dataset_id

        variant_config: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.variant_config, Unset):
            variant_config = self.variant_config.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "simulator": simulator,
            "parca_dataset_id": parca_dataset_id,
        })
        if variant_config is not UNSET:
            field_dict["variant_config"] = variant_config

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.ecoli_simulation_request_variant_config import EcoliSimulationRequestVariantConfig
        from ..models.simulator_version import SimulatorVersion

        d = dict(src_dict)
        simulator = SimulatorVersion.from_dict(d.pop("simulator"))

        parca_dataset_id = d.pop("parca_dataset_id")

        _variant_config = d.pop("variant_config", UNSET)
        variant_config: Union[Unset, EcoliSimulationRequestVariantConfig]
        if isinstance(_variant_config, Unset):
            variant_config = UNSET
        else:
            variant_config = EcoliSimulationRequestVariantConfig.from_dict(_variant_config)

        ecoli_simulation_request = cls(
            simulator=simulator,
            parca_dataset_id=parca_dataset_id,
            variant_config=variant_config,
        )

        ecoli_simulation_request.additional_properties = d
        return ecoli_simulation_request

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
