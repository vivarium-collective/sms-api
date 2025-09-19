from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.ecoli_experiment_dto_metadata import EcoliExperimentDTOMetadata
    from ..models.ecoli_experiment_request_dto import EcoliExperimentRequestDTO


T = TypeVar("T", bound="EcoliExperimentDTO")


@_attrs_define
class EcoliExperimentDTO:
    """
    Attributes:
        experiment_id (str):
        request (EcoliExperimentRequestDTO):
        last_updated (Union[Unset, str]):
        metadata (Union[Unset, EcoliExperimentDTOMetadata]):
        experiment_tag (Union[None, Unset, str]):
    """

    experiment_id: str
    request: "EcoliExperimentRequestDTO"
    last_updated: Union[Unset, str] = UNSET
    metadata: Union[Unset, "EcoliExperimentDTOMetadata"] = UNSET
    experiment_tag: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        experiment_id = self.experiment_id

        request = self.request.to_dict()

        last_updated = self.last_updated

        metadata: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.metadata, Unset):
            metadata = self.metadata.to_dict()

        experiment_tag: Union[None, Unset, str]
        if isinstance(self.experiment_tag, Unset):
            experiment_tag = UNSET
        else:
            experiment_tag = self.experiment_tag

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "experiment_id": experiment_id,
                "request": request,
            }
        )
        if last_updated is not UNSET:
            field_dict["last_updated"] = last_updated
        if metadata is not UNSET:
            field_dict["metadata"] = metadata
        if experiment_tag is not UNSET:
            field_dict["experiment_tag"] = experiment_tag

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.ecoli_experiment_dto_metadata import EcoliExperimentDTOMetadata
        from ..models.ecoli_experiment_request_dto import EcoliExperimentRequestDTO

        d = dict(src_dict)
        experiment_id = d.pop("experiment_id")

        request = EcoliExperimentRequestDTO.from_dict(d.pop("request"))

        last_updated = d.pop("last_updated", UNSET)

        _metadata = d.pop("metadata", UNSET)
        metadata: Union[Unset, EcoliExperimentDTOMetadata]
        if isinstance(_metadata, Unset):
            metadata = UNSET
        else:
            metadata = EcoliExperimentDTOMetadata.from_dict(_metadata)

        def _parse_experiment_tag(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        experiment_tag = _parse_experiment_tag(d.pop("experiment_tag", UNSET))

        ecoli_experiment_dto = cls(
            experiment_id=experiment_id,
            request=request,
            last_updated=last_updated,
            metadata=metadata,
            experiment_tag=experiment_tag,
        )

        ecoli_experiment_dto.additional_properties = d
        return ecoli_experiment_dto

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
