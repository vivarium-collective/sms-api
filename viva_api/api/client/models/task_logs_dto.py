from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..models.job_status import JobStatus
from ..types import UNSET, Unset

T = TypeVar("T", bound="TaskLogsDTO")


@_attrs_define
class TaskLogsDTO:
    """A task run's CloudWatch logs (viva-api#631 slice 3). ``lines`` is empty
    until the container has started (no log stream yet) or when no log group can
    be resolved; ``status`` lets the caller decide whether to keep polling.

        Attributes:
            task_id (int):
            job_id_ext (Union[None, Unset, str]):
            status (Union[JobStatus, None, Unset]):
            log_stream (Union[None, Unset, str]):
            lines (Union[Unset, list[str]]):
            report_uri (Union[None, Unset, str]):
    """

    task_id: int
    job_id_ext: Union[None, Unset, str] = UNSET
    status: Union[JobStatus, None, Unset] = UNSET
    log_stream: Union[None, Unset, str] = UNSET
    lines: Union[Unset, list[str]] = UNSET
    report_uri: Union[None, Unset, str] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        task_id = self.task_id

        job_id_ext: Union[None, Unset, str]
        if isinstance(self.job_id_ext, Unset):
            job_id_ext = UNSET
        else:
            job_id_ext = self.job_id_ext

        status: Union[None, Unset, str]
        if isinstance(self.status, Unset):
            status = UNSET
        elif isinstance(self.status, JobStatus):
            status = self.status.value
        else:
            status = self.status

        log_stream: Union[None, Unset, str]
        if isinstance(self.log_stream, Unset):
            log_stream = UNSET
        else:
            log_stream = self.log_stream

        lines: Union[Unset, list[str]] = UNSET
        if not isinstance(self.lines, Unset):
            lines = self.lines

        report_uri: Union[None, Unset, str]
        if isinstance(self.report_uri, Unset):
            report_uri = UNSET
        else:
            report_uri = self.report_uri

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "task_id": task_id,
        })
        if job_id_ext is not UNSET:
            field_dict["job_id_ext"] = job_id_ext
        if status is not UNSET:
            field_dict["status"] = status
        if log_stream is not UNSET:
            field_dict["log_stream"] = log_stream
        if lines is not UNSET:
            field_dict["lines"] = lines
        if report_uri is not UNSET:
            field_dict["report_uri"] = report_uri

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        task_id = d.pop("task_id")

        def _parse_job_id_ext(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        job_id_ext = _parse_job_id_ext(d.pop("job_id_ext", UNSET))

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

        def _parse_log_stream(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        log_stream = _parse_log_stream(d.pop("log_stream", UNSET))

        lines = cast(list[str], d.pop("lines", UNSET))

        def _parse_report_uri(data: object) -> Union[None, Unset, str]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, str], data)

        report_uri = _parse_report_uri(d.pop("report_uri", UNSET))

        task_logs_dto = cls(
            task_id=task_id,
            job_id_ext=job_id_ext,
            status=status,
            log_stream=log_stream,
            lines=lines,
            report_uri=report_uri,
        )

        task_logs_dto.additional_properties = d
        return task_logs_dto

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
