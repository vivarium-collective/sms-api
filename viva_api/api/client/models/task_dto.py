from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.job_status import JobStatus
from ..types import UNSET, Unset

if TYPE_CHECKING:
    from ..models.task_dto_sim_data_refs_type_0 import TaskDTOSimDataRefsType0


T = TypeVar("T", bound="TaskDTO")


@_attrs_define
class TaskDTO:
    """A task run's tracked state (submit response and status share this shape).

    Attributes:
        database_id (int):
        name (str):
        script (str):
        args (Union[Unset, list[str]]):
        sim_data_refs (Union['TaskDTOSimDataRefsType0', None, Unset]):
        memory_class (Union[None, Unset, str]):
        status (Union[JobStatus, None, Unset]):
        job_id_ext (Union[None, Unset, str]):
        out_uri (Union[None, Unset, str]):
        result_uri (Union[None, Unset, str]):
        error_message (Union[None, Unset, str]):
    """

    database_id: int
    name: str
    script: str
    args: Union[Unset, list[str]] = UNSET
    sim_data_refs: Union["TaskDTOSimDataRefsType0", None, Unset] = UNSET
    memory_class: Union[None, Unset, str] = UNSET
    status: Union[JobStatus, None, Unset] = UNSET
    job_id_ext: Union[None, Unset, str] = UNSET
    out_uri: Union[None, Unset, str] = UNSET
    result_uri: Union[None, Unset, str] = UNSET
    error_message: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        from ..models.task_dto_sim_data_refs_type_0 import TaskDTOSimDataRefsType0

        database_id = self.database_id

        name = self.name

        script = self.script

        args: Union[Unset, list[str]] = UNSET
        if not isinstance(self.args, Unset):
            args = self.args

        sim_data_refs: Union[None, Unset, dict[str, Any]]
        if isinstance(self.sim_data_refs, Unset):
            sim_data_refs = UNSET
        elif isinstance(self.sim_data_refs, TaskDTOSimDataRefsType0):
            sim_data_refs = self.sim_data_refs.to_dict()
        else:
            sim_data_refs = self.sim_data_refs

        memory_class: Union[None, Unset, str]
        if isinstance(self.memory_class, Unset):
            memory_class = UNSET
        else:
            memory_class = self.memory_class

        status: Union[None, Unset, str]
        if isinstance(self.status, Unset):
            status = UNSET
        elif isinstance(self.status, JobStatus):
            status = self.status.value
        else:
            status = self.status

        job_id_ext: Union[None, Unset, str]
        if isinstance(self.job_id_ext, Unset):
            job_id_ext = UNSET
        else:
            job_id_ext = self.job_id_ext

        out_uri: Union[None, Unset, str]
        if isinstance(self.out_uri, Unset):
            out_uri = UNSET
        else:
            out_uri = self.out_uri

        result_uri: Union[None, Unset, str]
        if isinstance(self.result_uri, Unset):
            result_uri = UNSET
        else:
            result_uri = self.result_uri

        error_message: Union[None, Unset, str]
        if isinstance(self.error_message, Unset):
            error_message = UNSET
        else:
            error_message = self.error_message

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "database_id": database_id,
                "name": name,
                "script": script,
            }
        )
        if args is not UNSET:
            field_dict["args"] = args
        if sim_data_refs is not UNSET:
            field_dict["sim_data_refs"] = sim_data_refs
        if memory_class is not UNSET:
            field_dict["memory_class"] = memory_class
        if status is not UNSET:
            field_dict["status"] = status
        if job_id_ext is not UNSET:
            field_dict["job_id_ext"] = job_id_ext
        if out_uri is not UNSET:
            field_dict["out_uri"] = out_uri
        if result_uri is not UNSET:
            field_dict["result_uri"] = result_uri
        if error_message is not UNSET:
            field_dict["error_message"] = error_message

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.task_dto_sim_data_refs_type_0 import TaskDTOSimDataRefsType0

        d = dict(src_dict)
        database_id = d.pop("database_id")

        name = d.pop("name")

        script = d.pop("script")

        args = cast(list[str], d.pop("args", UNSET))

        def _parse_sim_data_refs(data: object) -> Union["TaskDTOSimDataRefsType0", None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                sim_data_refs_type_0 = TaskDTOSimDataRefsType0.from_dict(data)

                return sim_data_refs_type_0
            except:  # noqa: E722
                pass
            return cast(Union["TaskDTOSimDataRefsType0", None, Unset], data)

        sim_data_refs = _parse_sim_data_refs(d.pop("sim_data_refs", UNSET))

        def _parse_memory_class(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        memory_class = _parse_memory_class(d.pop("memory_class", UNSET))

        def _parse_status(data: object) -> Union[JobStatus, None, Unset]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                status_type_0 = JobStatus(data)

                return status_type_0
            except:  # noqa: E722
                pass
            return cast(Union[JobStatus, None, Unset], data)

        status = _parse_status(d.pop("status", UNSET))

        def _parse_job_id_ext(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        job_id_ext = _parse_job_id_ext(d.pop("job_id_ext", UNSET))

        def _parse_out_uri(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        out_uri = _parse_out_uri(d.pop("out_uri", UNSET))

        def _parse_result_uri(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        result_uri = _parse_result_uri(d.pop("result_uri", UNSET))

        def _parse_error_message(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        error_message = _parse_error_message(d.pop("error_message", UNSET))

        task_dto = cls(
            database_id=database_id,
            name=name,
            script=script,
            args=args,
            sim_data_refs=sim_data_refs,
            memory_class=memory_class,
            status=status,
            job_id_ext=job_id_ext,
            out_uri=out_uri,
            result_uri=result_uri,
            error_message=error_message,
        )

        task_dto.additional_properties = d
        return task_dto

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
