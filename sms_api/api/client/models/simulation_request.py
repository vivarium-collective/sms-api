from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

if TYPE_CHECKING:
    from ..models.experiment_request import ExperimentRequest


T = TypeVar("T", bound="SimulationRequest")


@_attrs_define
class SimulationRequest:
    """Used by the /simulation endpoint.

    Attributes:
        simulator_id (int):
        parca_dataset_id (int):
        experiment (ExperimentRequest): Used by the /simulation endpoint.
    """

    simulator_id: int
    parca_dataset_id: int
    experiment: "ExperimentRequest"
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        simulator_id = self.simulator_id

        parca_dataset_id = self.parca_dataset_id

        experiment = self.experiment.to_dict()

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "simulator_id": simulator_id,
                "parca_dataset_id": parca_dataset_id,
                "experiment": experiment,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.experiment_request import ExperimentRequest

        d = dict(src_dict)
        simulator_id = d.pop("simulator_id")

        parca_dataset_id = d.pop("parca_dataset_id")

        experiment = ExperimentRequest.from_dict(d.pop("experiment"))

        simulation_request = cls(
            simulator_id=simulator_id,
            parca_dataset_id=parca_dataset_id,
            experiment=experiment,
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
