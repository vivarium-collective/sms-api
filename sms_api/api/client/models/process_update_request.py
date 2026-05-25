from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.process_update_request_state import ProcessUpdateRequestState


T = TypeVar("T", bound="ProcessUpdateRequest")


@_attrs_define
class ProcessUpdateRequest:
    """
    Attributes:
        state (Union[Unset, ProcessUpdateRequestState]): Current state to pass to process.update().
        interval (Union[Unset, float]): Time interval for this update step. Default: 1.0.
    """

    state: Union[Unset, "ProcessUpdateRequestState"] = UNSET
    interval: Union[Unset, float] = 1.0
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        state: Union[Unset, dict[str, Any]] = UNSET
        if not isinstance(self.state, Unset):
            state = self.state.to_dict()

        interval = self.interval

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({})
        if state is not UNSET:
            field_dict["state"] = state
        if interval is not UNSET:
            field_dict["interval"] = interval

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.process_update_request_state import ProcessUpdateRequestState

        d = dict(src_dict)
        _state = d.pop("state", UNSET)
        state: Union[Unset, ProcessUpdateRequestState]
        if isinstance(_state, Unset):
            state = UNSET
        else:
            state = ProcessUpdateRequestState.from_dict(_state)

        interval = d.pop("interval", UNSET)

        process_update_request = cls(
            state=state,
            interval=interval,
        )

        process_update_request.additional_properties = d
        return process_update_request

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
