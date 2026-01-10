from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.simulation_config import SimulationConfig
    from ..models.simulator import Simulator


T = TypeVar("T", bound="SimulationRequest")


@_attrs_define
class SimulationRequest:
    """Used by the /simulation endpoint.

    Attributes:
        config (SimulationConfig):
        simulator (Union['Simulator', None, Unset]):
        simulator_id (Union[None, Unset, int]):
        parca_dataset_id (Union[None, Unset, int]):
    """

    config: "SimulationConfig"
    simulator: Union["Simulator", None, Unset] = UNSET
    simulator_id: Union[None, Unset, int] = UNSET
    parca_dataset_id: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.simulator import Simulator

        config = self.config.to_dict()

        simulator: Union[None, Unset, dict[str, Any]]
        if isinstance(self.simulator, Unset):
            simulator = UNSET
        elif isinstance(self.simulator, Simulator):
            simulator = self.simulator.to_dict()
        else:
            simulator = self.simulator

        simulator_id: Union[None, Unset, int]
        if isinstance(self.simulator_id, Unset):
            simulator_id = UNSET
        else:
            simulator_id = self.simulator_id

        parca_dataset_id: Union[None, Unset, int]
        if isinstance(self.parca_dataset_id, Unset):
            parca_dataset_id = UNSET
        else:
            parca_dataset_id = self.parca_dataset_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "config": config,
            }
        )
        if simulator is not UNSET:
            field_dict["simulator"] = simulator
        if simulator_id is not UNSET:
            field_dict["simulator_id"] = simulator_id
        if parca_dataset_id is not UNSET:
            field_dict["parca_dataset_id"] = parca_dataset_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.simulation_config import SimulationConfig
        from ..models.simulator import Simulator

        d = dict(src_dict)
        config = SimulationConfig.from_dict(d.pop("config"))

        def _parse_simulator(data: object) -> Union["Simulator", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                simulator_type_0 = Simulator.from_dict(data)

                return simulator_type_0
            except:  # noqa: E722
                pass
            return cast(Union["Simulator", None, Unset], data)

        simulator = _parse_simulator(d.pop("simulator", UNSET))

        def _parse_simulator_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        simulator_id = _parse_simulator_id(d.pop("simulator_id", UNSET))

        def _parse_parca_dataset_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        parca_dataset_id = _parse_parca_dataset_id(d.pop("parca_dataset_id", UNSET))

        simulation_request = cls(
            config=config,
            simulator=simulator,
            simulator_id=simulator_id,
            parca_dataset_id=parca_dataset_id,
        )

        simulation_request.additional_properties = d
        return simulation_request

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
