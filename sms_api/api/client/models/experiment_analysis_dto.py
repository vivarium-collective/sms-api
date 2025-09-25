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
    from ..models.analysis_config import AnalysisConfig


T = TypeVar("T", bound="ExperimentAnalysisDTO")


@_attrs_define
class ExperimentAnalysisDTO:
    """
    Attributes:
        database_id (int):
        name (str):
        config (AnalysisConfig):
        last_updated (str):
        job_name (Union[None, Unset, str]):
        job_id (Union[None, Unset, int]):
    """

    database_id: int
    name: str
    config: "AnalysisConfig"
    last_updated: str
    job_name: Union[None, Unset, str] = UNSET
    job_id: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.analysis_config import AnalysisConfig

        database_id = self.database_id

        name = self.name

        config = self.config.to_dict()

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
            "last_updated": last_updated,
        })
        if job_name is not UNSET:
            field_dict["job_name"] = job_name
        if job_id is not UNSET:
            field_dict["job_id"] = job_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.analysis_config import AnalysisConfig

        d = dict(src_dict)
        database_id = d.pop("database_id")

        name = d.pop("name")

        config = AnalysisConfig.from_dict(d.pop("config"))

        last_updated = d.pop("last_updated")

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

        experiment_analysis_dto = cls(
            database_id=database_id,
            name=name,
            config=config,
            last_updated=last_updated,
            job_name=job_name,
            job_id=job_id,
        )

        experiment_analysis_dto.additional_properties = d
        return experiment_analysis_dto

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
