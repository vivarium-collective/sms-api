import logging
import pprint
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from sms_api.common.models import JobStatus

logger = logging.getLogger(__name__)


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

    def get_job_status(self) -> "JobStatus":
        """Map SLURM job state to JobStatus enum."""
        from sms_api.common.models import JobStatus

        state_upper = self.job_state.upper()
        if state_upper in ("PENDING", "PD"):
            return JobStatus.PENDING
        elif state_upper in ("RUNNING", "R"):
            return JobStatus.RUNNING
        elif state_upper in ("COMPLETED", "CD"):
            return JobStatus.COMPLETED
        elif state_upper in ("FAILED", "F", "CANCELLED", "CA", "TIMEOUT", "TO", "NODE_FAIL", "NF"):
            return JobStatus.FAILED
        else:
            logger.warning(f"Unknown SLURM state '{self.job_state}', defaulting to PENDING")
            return JobStatus.PENDING

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


# =============================================================================
# Nextflow Weblog Event Models
# =============================================================================


class NextflowEventType(str, Enum):
    """Nextflow weblog event types."""

    STARTED = "started"
    COMPLETED = "completed"
    PROCESS_SUBMITTED = "process_submitted"
    PROCESS_STARTED = "process_started"
    PROCESS_COMPLETED = "process_completed"


class NextflowTraceStatus(str, Enum):
    """Nextflow trace task status values."""

    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CACHED = "CACHED"
    ABORTED = "ABORTED"


class NextflowDateTime(BaseModel):
    """Nextflow's custom datetime representation."""

    model_config = ConfigDict(populate_by_name=True)

    day_of_month: int = Field(alias="dayOfMonth")
    day_of_week: str = Field(alias="dayOfWeek")
    day_of_year: int = Field(alias="dayOfYear")
    hour: int
    minute: int
    second: int
    nano: int
    month: str
    month_value: int = Field(alias="monthValue")
    year: int
    offset: Optional[dict[str, Any]] = None

    def to_datetime(self) -> datetime:
        """Convert to Python datetime."""
        return datetime(
            year=self.year,
            month=self.month_value,
            day=self.day_of_month,
            hour=self.hour,
            minute=self.minute,
            second=self.second,
            microsecond=self.nano // 1000,
        )


class NextflowVersion(BaseModel):
    """Nextflow version information."""

    version: str
    build: int
    timestamp: str
    enable: dict[str, Any] = Field(default_factory=dict)


class NextflowWave(BaseModel):
    """Nextflow Wave configuration."""

    enabled: bool = False


class NextflowFusion(BaseModel):
    """Nextflow Fusion configuration."""

    enabled: bool = False
    version: Optional[str] = None


class NextflowProcessStats(BaseModel):
    """Statistics for a single Nextflow process."""

    model_config = ConfigDict(populate_by_name=True)

    index: int
    name: str
    hash: Optional[str] = None
    task_name: Optional[str] = Field(default=None, alias="taskName")
    pending: int = 0
    submitted: int = 0
    running: int = 0
    succeeded: int = 0
    cached: int = 0
    failed: int = 0
    aborted: int = 0
    stored: int = 0
    ignored: int = 0
    retries: int = 0
    terminated: bool = False
    errored: bool = False
    load_cpus: int = Field(default=0, alias="loadCpus")
    load_memory: int = Field(default=0, alias="loadMemory")
    peak_running: int = Field(default=0, alias="peakRunning")
    peak_cpus: int = Field(default=0, alias="peakCpus")
    peak_memory: int = Field(default=0, alias="peakMemory")
    completed_count: int = Field(default=0, alias="completedCount")
    total_count: int = Field(default=0, alias="totalCount")


class NextflowStats(BaseModel):
    """Nextflow workflow statistics."""

    model_config = ConfigDict(populate_by_name=True)

    change_timestamp: int = Field(default=0, alias="changeTimestamp")
    succeeded_count: int = Field(default=0, alias="succeededCount")
    cached_count: int = Field(default=0, alias="cachedCount")
    failed_count: int = Field(default=0, alias="failedCount")
    ignored_count: int = Field(default=0, alias="ignoredCount")
    pending_count: int = Field(default=0, alias="pendingCount")
    submitted_count: int = Field(default=0, alias="submittedCount")
    running_count: int = Field(default=0, alias="runningCount")
    retries_count: int = Field(default=0, alias="retriesCount")
    aborted_count: int = Field(default=0, alias="abortedCount")
    load_cpus: int = Field(default=0, alias="loadCpus")
    load_memory: int = Field(default=0, alias="loadMemory")
    peak_running: int = Field(default=0, alias="peakRunning")
    peak_cpus: int = Field(default=0, alias="peakCpus")
    peak_memory: int = Field(default=0, alias="peakMemory")
    cached_duration: int = Field(default=0, alias="cachedDuration")
    cached_pct: float = Field(default=0.0, alias="cachedPct")
    failed_duration: int = Field(default=0, alias="failedDuration")
    succeed_count: int = Field(default=0, alias="succeedCount")
    succeed_duration: int = Field(default=0, alias="succeedDuration")
    succeed_pct: float = Field(default=0.0, alias="succeedPct")
    total_count: int = Field(default=0, alias="totalCount")
    progress_length: int = Field(default=0, alias="progressLength")
    processes: list[NextflowProcessStats] = Field(default_factory=list)


class NextflowManifest(BaseModel):
    """Nextflow workflow manifest information."""

    model_config = ConfigDict(populate_by_name=True)

    author: Optional[str] = None
    contributors: list[Any] = Field(default_factory=list)
    default_branch: Optional[str] = Field(default=None, alias="defaultBranch")
    description: Optional[str] = None
    docs_url: Optional[str] = Field(default=None, alias="docsUrl")
    doi: Optional[str] = None
    gitmodules: Optional[str] = None
    home_page: Optional[str] = Field(default=None, alias="homePage")
    icon: Optional[str] = None
    license: Optional[str] = None
    main_script: str = Field(default="main.nf", alias="mainScript")
    name: Optional[str] = None
    nextflow_version: Optional[str] = Field(default=None, alias="nextflowVersion")
    organization: Optional[str] = None
    recurse_submodules: bool = Field(default=False, alias="recurseSubmodules")
    version: Optional[str] = None


class NextflowWorkflow(BaseModel):
    """Nextflow workflow metadata."""

    model_config = ConfigDict(populate_by_name=True)

    run_name: str = Field(alias="runName")
    script_id: str = Field(alias="scriptId")
    script_file: str = Field(alias="scriptFile")
    script_name: str = Field(alias="scriptName")
    repository: Optional[str] = None
    commit_id: Optional[str] = Field(default=None, alias="commitId")
    revision: Optional[str] = None
    start: Optional[NextflowDateTime] = None
    complete: Optional[NextflowDateTime] = None
    duration: Optional[int] = None
    container: dict[str, Any] = Field(default_factory=dict)
    command_line: str = Field(alias="commandLine")
    nextflow: NextflowVersion
    success: bool
    project_dir: str = Field(alias="projectDir")
    project_name: str = Field(alias="projectName")
    launch_dir: str = Field(alias="launchDir")
    output_dir: str = Field(alias="outputDir")
    work_dir: str = Field(alias="workDir")
    home_dir: str = Field(alias="homeDir")
    user_name: str = Field(alias="userName")
    exit_status: Optional[int] = Field(default=None, alias="exitStatus")
    error_message: Optional[str] = Field(default=None, alias="errorMessage")
    error_report: Optional[str] = Field(default=None, alias="errorReport")
    profile: str
    session_id: str = Field(alias="sessionId")
    resume: bool = False
    stub_run: bool = Field(default=False, alias="stubRun")
    preview: bool = False
    container_engine: Optional[str] = Field(default=None, alias="containerEngine")
    wave: NextflowWave = Field(default_factory=NextflowWave)
    fusion: NextflowFusion = Field(default_factory=NextflowFusion)
    config_files: list[str] = Field(default_factory=list, alias="configFiles")
    stats: NextflowStats = Field(default_factory=NextflowStats)
    manifest: NextflowManifest = Field(default_factory=NextflowManifest)
    fail_on_ignore: bool = Field(default=False, alias="failOnIgnore")


class NextflowMetadata(BaseModel):
    """Nextflow metadata payload for started/completed events."""

    parameters: dict[str, Any] = Field(default_factory=dict)
    workflow: NextflowWorkflow


class NextflowTrace(BaseModel):
    """Nextflow trace payload for process events."""

    model_config = ConfigDict(populate_by_name=True)

    task_id: int = Field(alias="task_id")
    status: NextflowTraceStatus
    hash: str
    name: str
    exit: int
    submit: int
    start: int
    process: str
    tag: Optional[str] = None
    module: list[str] = Field(default_factory=list)
    container: Optional[str] = None
    attempt: int = 1
    script: str
    scratch: Optional[str] = None
    workdir: str
    queue: Optional[str] = None
    cpus: int = 1
    memory: Optional[int] = None
    disk: Optional[int] = None
    time: Optional[int] = None
    env: Optional[str] = None
    native_id: Optional[int] = None
    error_action: Optional[str] = None
    complete: Optional[int] = None
    duration: Optional[int] = None
    realtime: Optional[int] = None
    percent_cpu: Optional[float] = Field(default=None, alias="%cpu")
    cpu_model: Optional[str] = None
    rchar: Optional[int] = None
    wchar: Optional[int] = None
    syscr: Optional[int] = None
    syscw: Optional[int] = None
    read_bytes: Optional[int] = None
    write_bytes: Optional[int] = None
    percent_mem: Optional[float] = Field(default=None, alias="%mem")
    vmem: Optional[int] = None
    rss: Optional[int] = None
    peak_vmem: Optional[int] = None
    peak_rss: Optional[int] = None
    vol_ctxt: Optional[int] = None
    inv_ctxt: Optional[int] = None

    def is_completed(self) -> bool:
        """Check if the task has completed (successfully or failed)."""
        return self.status in (
            NextflowTraceStatus.COMPLETED,
            NextflowTraceStatus.FAILED,
            NextflowTraceStatus.CACHED,
            NextflowTraceStatus.ABORTED,
        )


class NextflowMetadataEvent(BaseModel):
    """Nextflow weblog event containing workflow metadata (started/completed)."""

    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    event: Literal["started", "completed"]
    run_name: str = Field(alias="runName")
    utc_time: str = Field(alias="utcTime")
    metadata: NextflowMetadata


class NextflowTraceEvent(BaseModel):
    """Nextflow weblog event containing task trace data."""

    model_config = ConfigDict(populate_by_name=True)

    run_id: str = Field(alias="runId")
    event: Literal["process_submitted", "process_started", "process_completed"]
    run_name: str = Field(alias="runName")
    utc_time: str = Field(alias="utcTime")
    trace: NextflowTrace


NextflowEvent = Union[NextflowMetadataEvent, NextflowTraceEvent]


def parse_nextflow_event(data: dict[str, Any]) -> NextflowEvent:
    """Parse a Nextflow weblog event from a dictionary.

    Args:
        data: Dictionary containing the event data (parsed from JSON)

    Returns:
        Either a NextflowMetadataEvent or NextflowTraceEvent

    Raises:
        ValueError: If the event type is unknown
    """
    event_type = data.get("event")
    if event_type in ("started", "completed"):
        return NextflowMetadataEvent.model_validate(data)
    elif event_type in ("process_submitted", "process_started", "process_completed"):
        return NextflowTraceEvent.model_validate(data)
    else:
        raise ValueError(f"Unknown Nextflow event type: {event_type}")
