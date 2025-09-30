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
    from ..models.experiment_metadata import ExperimentMetadata
    from ..models.simulation_config import SimulationConfig


T = TypeVar("T", bound="EcoliSimulationDTO")


@_attrs_define
class EcoliSimulationDTO:
    """Used by the /simulation endpoint

    Attributes:
        database_id (int):
        name (str):
        config (SimulationConfig):
        metadata (ExperimentMetadata):
        last_updated (Union[Unset, str]):
        job_name (Union[None, Unset, str]):
        job_id (Union[None, Unset, int]):
    """

    database_id: int
    name: str
    config: "SimulationConfig"
    metadata: "ExperimentMetadata"
    last_updated: Union[Unset, str] = UNSET
    job_name: Union[None, Unset, str] = UNSET
    job_id: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.experiment_metadata import ExperimentMetadata
        from ..models.simulation_config import SimulationConfig

        database_id = self.database_id

        name = self.name

        config = self.config.to_dict()

        metadata = self.metadata.to_dict()

        last_updated = self.last_updated

        job_name: Union[None, Unset, str]
        if isinstance(self.job_name, Unset):
            job_name = UNSET
        else:
            job_name = self.job_name

        job_id: Union[None, Unset, int]
        if isinstance(self.job_id, Unset):
            job_id = UNSET
        else:
            job_id = self.job_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "database_id": database_id,
            "name": name,
            "config": config,
            "metadata": metadata,
        })
        if last_updated is not UNSET:
            field_dict["last_updated"] = last_updated
        if job_name is not UNSET:
            field_dict["job_name"] = job_name
        if job_id is not UNSET:
            field_dict["job_id"] = job_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.experiment_metadata import ExperimentMetadata
        from ..models.simulation_config import SimulationConfig

        d = dict(src_dict)
        database_id = d.pop("database_id")

        name = d.pop("name")

        config = SimulationConfig.from_dict(d.pop("config"))

        metadata = ExperimentMetadata.from_dict(d.pop("metadata"))

        last_updated = d.pop("last_updated", UNSET)

        def _parse_job_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        job_name = _parse_job_name(d.pop("job_name", UNSET))

        def _parse_job_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        job_id = _parse_job_id(d.pop("job_id", UNSET))

        ecoli_simulation_dto = cls(
            database_id=database_id,
            name=name,
            config=config,
            metadata=metadata,
            last_updated=last_updated,
            job_name=job_name,
            job_id=job_id,
        )

        ecoli_simulation_dto.additional_properties = d
        return ecoli_simulation_dto

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
