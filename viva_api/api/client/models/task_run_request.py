from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.task_run_request_sim_data_refs_type_0 import TaskRunRequestSimDataRefsType0


T = TypeVar("T", bound="TaskRunRequest")


@_attrs_define
class TaskRunRequest:
    """Request to run a self-contained script on the in-region task compute
    (viva-api#631). Slice 1: ``script`` is a path to a script already in the
    image (e.g. an fss-combine / ptools-regather turnkey script that lives in the
    repo). ``memory_class`` routes the instance via the same mechanism as
    analyses (viva-api#629).

        Attributes:
            script (str):
            args (Union[Unset, list[str]]):
            sim_data_refs (Union['TaskRunRequestSimDataRefsType0', None, Unset]):
            memory_class (Union[Unset, str]):  Default: 'standard'.
            commit (Union[None, Unset, str]):
            name (Union[None, Unset, str]):
    """

    script: str
    args: Union[Unset, list[str]] = UNSET
    sim_data_refs: Union["TaskRunRequestSimDataRefsType0", None, Unset] = UNSET
    memory_class: Union[Unset, str] = "standard"
    commit: Union[None, Unset, str] = UNSET
    name: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.task_run_request_sim_data_refs_type_0 import TaskRunRequestSimDataRefsType0

        script = self.script

        args: Union[Unset, list[str]] = UNSET
        if not isinstance(self.args, Unset):
            args = self.args

        sim_data_refs: Union[None, Unset, dict[str, Any]]
        if isinstance(self.sim_data_refs, Unset):
            sim_data_refs = UNSET
        elif isinstance(self.sim_data_refs, TaskRunRequestSimDataRefsType0):
            sim_data_refs = self.sim_data_refs.to_dict()
        else:
            sim_data_refs = self.sim_data_refs

        memory_class = self.memory_class

        commit: Union[None, Unset, str]
        if isinstance(self.commit, Unset):
            commit = UNSET
        else:
            commit = self.commit

        name: Union[None, Unset, str]
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "script": script,
        })
        if args is not UNSET:
            field_dict["args"] = args
        if sim_data_refs is not UNSET:
            field_dict["sim_data_refs"] = sim_data_refs
        if memory_class is not UNSET:
            field_dict["memory_class"] = memory_class
        if commit is not UNSET:
            field_dict["commit"] = commit
        if name is not UNSET:
            field_dict["name"] = name

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.task_run_request_sim_data_refs_type_0 import TaskRunRequestSimDataRefsType0

        d = dict(src_dict)
        script = d.pop("script")

        args = cast(list[str], d.pop("args", UNSET))

        def _parse_sim_data_refs(data: object) -> Union["TaskRunRequestSimDataRefsType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                sim_data_refs_type_0 = TaskRunRequestSimDataRefsType0.from_dict(data)

                return sim_data_refs_type_0
            except:  # noqa: E722
                pass
            return cast(Union["TaskRunRequestSimDataRefsType0", None, Unset], data)

        sim_data_refs = _parse_sim_data_refs(d.pop("sim_data_refs", UNSET))

        memory_class = d.pop("memory_class", UNSET)

        def _parse_commit(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        commit = _parse_commit(d.pop("commit", UNSET))

        def _parse_name(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        name = _parse_name(d.pop("name", UNSET))

        task_run_request = cls(
            script=script,
            args=args,
            sim_data_refs=sim_data_refs,
            memory_class=memory_class,
            commit=commit,
            name=name,
        )

        task_run_request.additional_properties = d
        return task_run_request

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
