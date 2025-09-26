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
    from ..models.experiment_request import ExperimentRequest


T = TypeVar("T", bound="BodyRunEcoliSimulation")


@_attrs_define
class BodyRunEcoliSimulation:
    """
    Attributes:
        request (Union[Unset, ExperimentRequest]): Used by the /simulation endpoint.
        metadata (Union['ExperimentMetadata', None, Unset]):
    """

    request: Union[Unset, "ExperimentRequest"] = UNSET
    metadata: Union["ExperimentMetadata", None, Unset] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.experiment_metadata import ExperimentMetadata
        from ..models.experiment_request import ExperimentRequest

        request: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.request, Unset):
            request = self.request.to_dict()

        metadata: Union[None, Unset, dict[str, Any]]
        if isinstance(self.metadata, Unset):
            metadata = UNSET
        elif isinstance(self.metadata, ExperimentMetadata):
            metadata = self.metadata.to_dict()
        else:
            metadata = self.metadata

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if request is not UNSET:
            field_dict["request"] = request
        if metadata is not UNSET:
            field_dict["metadata"] = metadata

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.experiment_metadata import ExperimentMetadata
        from ..models.experiment_request import ExperimentRequest

        d = dict(src_dict)
        _request = d.pop("request", UNSET)
        request: Union[Unset, ExperimentRequest]
        if isinstance(_request, Unset):
            request = UNSET
        else:
            request = ExperimentRequest.from_dict(_request)

        def _parse_metadata(data: object) -> Union["ExperimentMetadata", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                metadata_type_0 = ExperimentMetadata.from_dict(data)

                return metadata_type_0
            except:  # noqa: E722
                pass
            return cast(Union["ExperimentMetadata", None, Unset], data)

        metadata = _parse_metadata(d.pop("metadata", UNSET))

        body_run_ecoli_simulation = cls(
            request=request,
            metadata=metadata,
        )

        body_run_ecoli_simulation.additional_properties = d
        return body_run_ecoli_simulation

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
