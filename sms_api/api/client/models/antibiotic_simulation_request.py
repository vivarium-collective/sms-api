from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import Union

if TYPE_CHECKING:
    from ..models.simulator_version import SimulatorVersion
    from ..models.antibiotic_simulation_request_variant_config import AntibioticSimulationRequestVariantConfig
    from ..models.antibiotic_simulation_request_antibiotics_config import AntibioticSimulationRequestAntibioticsConfig


T = TypeVar("T", bound="AntibioticSimulationRequest")


@_attrs_define
class AntibioticSimulationRequest:
    """
    Attributes:
        simulator (SimulatorVersion):
        parca_dataset_id (int):
        variant_config (AntibioticSimulationRequestVariantConfig):
        antibiotics_config (Union[Unset, AntibioticSimulationRequestAntibioticsConfig]):
    """

    simulator: "SimulatorVersion"
    parca_dataset_id: int
    variant_config: "AntibioticSimulationRequestVariantConfig"
    antibiotics_config: Union[Unset, "AntibioticSimulationRequestAntibioticsConfig"] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.simulator_version import SimulatorVersion
        from ..models.antibiotic_simulation_request_variant_config import AntibioticSimulationRequestVariantConfig
        from ..models.antibiotic_simulation_request_antibiotics_config import (
            AntibioticSimulationRequestAntibioticsConfig,
        )

        simulator = self.simulator.to_dict()

        parca_dataset_id = self.parca_dataset_id

        variant_config = self.variant_config.to_dict()

        antibiotics_config: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.antibiotics_config, Unset):
            antibiotics_config = self.antibiotics_config.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "simulator": simulator,
            "parca_dataset_id": parca_dataset_id,
            "variant_config": variant_config,
        })
        if antibiotics_config is not UNSET:
            field_dict["antibiotics_config"] = antibiotics_config

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.simulator_version import SimulatorVersion
        from ..models.antibiotic_simulation_request_variant_config import AntibioticSimulationRequestVariantConfig
        from ..models.antibiotic_simulation_request_antibiotics_config import (
            AntibioticSimulationRequestAntibioticsConfig,
        )

        d = dict(src_dict)
        simulator = SimulatorVersion.from_dict(d.pop("simulator"))

        parca_dataset_id = d.pop("parca_dataset_id")

        variant_config = AntibioticSimulationRequestVariantConfig.from_dict(d.pop("variant_config"))

        _antibiotics_config = d.pop("antibiotics_config", UNSET)
        antibiotics_config: Union[Unset, AntibioticSimulationRequestAntibioticsConfig]
        if isinstance(_antibiotics_config, Unset):
            antibiotics_config = UNSET
        else:
            antibiotics_config = AntibioticSimulationRequestAntibioticsConfig.from_dict(_antibiotics_config)

        antibiotic_simulation_request = cls(
            simulator=simulator,
            parca_dataset_id=parca_dataset_id,
            variant_config=variant_config,
            antibiotics_config=antibiotics_config,
        )

        antibiotic_simulation_request.additional_properties = d
        return antibiotic_simulation_request

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
