import pprint
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NumericSlurmValue(BaseModel):
    infinite: Optional[bool] = None
    number: Optional[int] = None
    set: Optional[bool] = None

class ExitCode(BaseModel):
    status: list[str]
    return_code: NumericSlurmValue

class SlurmJob(BaseModel):
    job_id: int
    name: str
    account: str
    batch_flag: bool
    batch_host: str
    cluster: str
    command: str
    user_name: str
    job_state: list[str]
    exit_code: Optional[ExitCode] = None
    node_count: Optional[NumericSlurmValue] = None
    cpus: Optional[NumericSlurmValue] = None
    array_job_id: Optional[NumericSlurmValue] = None
    array_task_id: Optional[NumericSlurmValue] = None
    array_max_tasks: Optional[NumericSlurmValue] = None

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        return self.model_dump_json(by_alias=True, exclude_unset=True)