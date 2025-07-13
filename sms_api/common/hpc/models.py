import pprint
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SlurmJob(BaseModel):
    #                                 --squeue--   --sacct--
    job_id: int  #                       %i          jobid
    name: str  #                         %j          jobname
    account: str  #                      %a          account
    user_name: str  #                    %u          user
    job_state: str  #                    %T          state
    start_time: Optional[str] = None  #              start
    end_time: Optional[str] = None  #                end
    elapsed: Optional[str] = None  #                elapsed
    exit_code: Optional[str] = None  #                exitcode

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

    def is_done(self) -> bool:
        """Check if the job is done based on its state."""
        if not self.job_state:
            return False
        return self.job_state.upper() in ["COMPLETED", "FAILED"]

    @staticmethod
    def get_sacct_format_string() -> str:
        return "jobid,jobname,account,user,state,start,end,elapsed,exitcode"

    @classmethod
    def from_sacct_formatted_output(cls, line: str) -> "SlurmJob":
        # Split the line by delimiter
        fields = line.strip().split("|")
        # Map fields to model attributes
        return cls(
            job_id=int(fields[0]),
            name=fields[1],
            account=fields[2],
            user_name=fields[3],
            job_state=fields[4],
            start_time=fields[5],
            end_time=fields[6],
            elapsed=fields[7],
            exit_code=fields[8],
        )

    @staticmethod
    def get_squeue_format_string() -> str:
        return "%i|%j|%a|%u|%T"

    @classmethod
    def from_squeue_formatted_output(cls, line: str) -> "SlurmJob":
        # Split the line by delimiter
        fields = line.strip().split("|")
        # Map fields to model attributes
        return cls(
            job_id=int(fields[0]),
            name=fields[1],
            account=fields[2],
            user_name=fields[3],
            job_state=fields[4],
        )
