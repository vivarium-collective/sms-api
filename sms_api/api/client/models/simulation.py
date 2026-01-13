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
    from ..models.simulation_config import SimulationConfig


T = TypeVar("T", bound="Simulation")


@_attrs_define
class Simulation:
    """Used by the /simulation endpoint

    Attributes:
        database_id (int):
        simulator_id (int):
        parca_dataset_id (int):
        config (SimulationConfig):
        last_updated (Union[Unset, str]):  Default: '2026-01-13 13:08:18.336429'.
        job_id (Union[None, Unset, int]):
    """

    database_id: int
    simulator_id: int
    parca_dataset_id: int
    config: "SimulationConfig"
    last_updated: Union[Unset, str] = "2026-01-13 13:08:18.336429"
    job_id: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.simulation_config import SimulationConfig

        database_id = self.database_id

        simulator_id = self.simulator_id

        parca_dataset_id = self.parca_dataset_id

        config = self.config.to_dict()

        last_updated = self.last_updated

        job_id: Union[None, Unset, int]
        if isinstance(self.job_id, Unset):
            job_id = UNSET
        else:
            job_id = self.job_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "database_id": database_id,
            "simulator_id": simulator_id,
            "parca_dataset_id": parca_dataset_id,
            "config": config,
        })
        if last_updated is not UNSET:
            field_dict["last_updated"] = last_updated
        if job_id is not UNSET:
            field_dict["job_id"] = job_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.simulation_config import SimulationConfig

        d = dict(src_dict)
        database_id = d.pop("database_id")

        simulator_id = d.pop("simulator_id")

        parca_dataset_id = d.pop("parca_dataset_id")

        config = SimulationConfig.from_dict(d.pop("config"))

        last_updated = d.pop("last_updated", UNSET)

        def _parse_job_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        job_id = _parse_job_id(d.pop("job_id", UNSET))

        simulation = cls(
            database_id=database_id,
            simulator_id=simulator_id,
            parca_dataset_id=parca_dataset_id,
            config=config,
            last_updated=last_updated,
            job_id=job_id,
        )

        simulation.additional_properties = d
        return simulation

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
