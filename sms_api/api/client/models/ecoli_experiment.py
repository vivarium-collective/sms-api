from collections.abc import Mapping
from typing import Any, TypeVar, Optional, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast
from typing import cast, Union
from typing import Union

if TYPE_CHECKING:
  from ..models.ecoli_simulation import EcoliSimulation
  from ..models.ecoli_experiment_metadata import EcoliExperimentMetadata
  from ..models.antibiotic_simulation import AntibioticSimulation





T = TypeVar("T", bound="EcoliExperiment")



@_attrs_define
class EcoliExperiment:
    """
        Attributes:
            experiment_id (str):
            simulation (Union['AntibioticSimulation', 'EcoliSimulation']):
            last_updated (Union[Unset, str]):
            metadata (Union[Unset, EcoliExperimentMetadata]):
     """

    experiment_id: str
    simulation: Union['AntibioticSimulation', 'EcoliSimulation']
    last_updated: Union[Unset, str] = UNSET
    metadata: Union[Unset, 'EcoliExperimentMetadata'] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.ecoli_simulation import EcoliSimulation
        from ..models.ecoli_experiment_metadata import EcoliExperimentMetadata
        from ..models.antibiotic_simulation import AntibioticSimulation
        experiment_id = self.experiment_id

        simulation: dict[str, Any]
        if isinstance(self.simulation, EcoliSimulation):
            simulation = self.simulation.to_dict()
        else:
            simulation = self.simulation.to_dict()


        last_updated = self.last_updated

        metadata: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.metadata, Unset):
            metadata = self.metadata.to_dict()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "experiment_id": experiment_id,
            "simulation": simulation,
        })
        if last_updated is not UNSET:
            field_dict["last_updated"] = last_updated
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.ecoli_simulation import EcoliSimulation
        from ..models.ecoli_experiment_metadata import EcoliExperimentMetadata
        from ..models.antibiotic_simulation import AntibioticSimulation
        d = dict(src_dict)
        experiment_id = d.pop("experiment_id")

        def _parse_simulation(data: object) -> Union['AntibioticSimulation', 'EcoliSimulation']:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                simulation_type_0 = EcoliSimulation.from_dict(data)



                return simulation_type_0
            except: # noqa: E722
                pass
            if not isinstance(data, dict):
                raise TypeError()
            simulation_type_1 = AntibioticSimulation.from_dict(data)



            return simulation_type_1

        simulation = _parse_simulation(d.pop("simulation"))


        last_updated = d.pop("last_updated", UNSET)

        _metadata = d.pop("metadata", UNSET)
        metadata: Union[Unset, EcoliExperimentMetadata]
        if isinstance(_metadata,  Unset):
            metadata = UNSET
        else:
            metadata = EcoliExperimentMetadata.from_dict(_metadata)




        ecoli_experiment = cls(
            experiment_id=experiment_id,
            simulation=simulation,
            last_updated=last_updated,
            metadata=metadata,
        )


        ecoli_experiment.additional_properties = d
        return ecoli_experiment

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
