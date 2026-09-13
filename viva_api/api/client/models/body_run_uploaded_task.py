from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from .. import types
from ..types import UNSET, Unset

T = TypeVar("T", bound="BodyRunUploadedTask")


@_attrs_define
class BodyRunUploadedTask:
    """
    Attributes:
        script (str): The script file to run.
        args (Union[Unset, list[str]]): Positional args passed to the script.
        sim_data_refs (Union[None, Unset, str]): JSON object of caller-defined sim-data references.
        memory_class (Union[Unset, str]):  Default: 'standard'.
        commit (Union[None, Unset, str]): Image commit to run in; default latest.
        name (Union[None, Unset, str]): Optional human label; defaults to the script name.
    """

    script: str
    args: Union[Unset, list[str]] = UNSET
    sim_data_refs: Union[None, Unset, str] = UNSET
    memory_class: Union[Unset, str] = "standard"
    commit: Union[None, Unset, str] = UNSET
    name: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        script = self.script

        args: Union[Unset, list[str]] = UNSET
        if not isinstance(self.args, Unset):
            args = self.args

        sim_data_refs: Union[None, Unset, str]
        if isinstance(self.sim_data_refs, Unset):
            sim_data_refs = UNSET
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

    def to_multipart(self) -> types.RequestFiles:
        files: types.RequestFiles = []

        files.append(("script", (None, str(self.script).encode(), "text/plain")))

        if not isinstance(self.args, Unset):
            for args_item_element in self.args:
                files.append(("args", (None, str(args_item_element).encode(), "text/plain")))

        if not isinstance(self.sim_data_refs, Unset):
            if isinstance(self.sim_data_refs, str):
                files.append(("sim_data_refs", (None, str(self.sim_data_refs).encode(), "text/plain")))
            else:
                files.append(("sim_data_refs", (None, str(self.sim_data_refs).encode(), "text/plain")))

        if not isinstance(self.memory_class, Unset):
            files.append(("memory_class", (None, str(self.memory_class).encode(), "text/plain")))

        if not isinstance(self.commit, Unset):
            if isinstance(self.commit, str):
                files.append(("commit", (None, str(self.commit).encode(), "text/plain")))
            else:
                files.append(("commit", (None, str(self.commit).encode(), "text/plain")))

        if not isinstance(self.name, Unset):
            if isinstance(self.name, str):
                files.append(("name", (None, str(self.name).encode(), "text/plain")))
            else:
                files.append(("name", (None, str(self.name).encode(), "text/plain")))

        for prop_name, prop in self.additional_properties.items():
            files.append((prop_name, (None, str(prop).encode(), "text/plain")))

        return files

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        script = d.pop("script")

        args = cast(list[str], d.pop("args", UNSET))

        def _parse_sim_data_refs(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

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

        body_run_uploaded_task = cls(
            script=script,
            args=args,
            sim_data_refs=sim_data_refs,
            memory_class=memory_class,
            commit=commit,
            name=name,
        )

        body_run_uploaded_task.additional_properties = d
        return body_run_uploaded_task

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
