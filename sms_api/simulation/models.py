import datetime
import enum
import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel as _BaseModel
from pydantic import Field


@dataclass
class FlexData:
    _data: dict[str, Any] = field(default_factory=dict)

    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        self._data = kwargs

    def __getattr__(self, item):  # type: ignore[no-untyped-def]
        return self._data[item]

    def __getitem__(self, item):  # type: ignore[no-untyped-def]
        return self._data[item]

    def keys(self):  # type: ignore[no-untyped-def]
        return self._data.keys()

    def dict(self) -> dict[str, Any]:
        return self._data


class Payload(FlexData):
    pass


class BaseModel(_BaseModel):
    def as_payload(self) -> Payload:
        serialized = json.loads(self.model_dump_json())
        return Payload(**serialized)


class JobType(enum.Enum):
    SIMULATION = "simulation"
    PARCA = "parca"
    BUILD_IMAGE = "build_image"


class JobStatus(StrEnum):
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HpcRun(BaseModel):
    database_id: int
    slurmjobid: int  # Slurm job ID if applicable
    correlation_id: str  # to correlate with the WorkerEvent, if applicable ("N/A" if not applicable)
    job_type: JobType
    ref_id: int  # primary key of the object this HPC run is associated with (sim, parca, etc.)
    status: JobStatus | None = None
    start_time: str | None = None  # ISO format datetime string
    end_time: str | None = None  # ISO format datetime string or None if still running
    error_message: str | None = None  # Error message if the simulation failed


class SimulationRun(BaseModel):
    id: str
    status: JobStatus


class Simulator(BaseModel):
    git_commit_hash: str  # Git commit hash for the specific simulator version (first 7 characters)
    git_repo_url: str  # Git repository URL for the simulator
    git_branch: str  # Git branch name for the simulator version


class SimulatorVersion(Simulator):
    database_id: int  # Unique identifier for the simulator version
    created_at: datetime.datetime | None = None


class RegisteredSimulators(BaseModel):
    versions: list[SimulatorVersion]
    timestamp: datetime.datetime | None = Field(default_factory=datetime.datetime.now)


class ParcaDatasetRequest(BaseModel):
    simulator_version: SimulatorVersion  # Version of the software used to generate the dataset
    parca_config: dict[str, int | float | str]

    @property
    def config_hash(self) -> str:
        """Generate a deep hash of the parca request for caching purposes."""
        json_str = json.dumps(self.parca_config)
        return hashlib.md5(json_str.encode()).hexdigest()  # noqa: S324 insecure hash `md5` is okay for caching


class ParcaDataset(BaseModel):
    database_id: int  # Unique identifier for the dataset
    parca_dataset_request: ParcaDatasetRequest  # Request parameters for the dataset
    remote_archive_path: str | None = None  # Path to the dataset archive in remote storage


class Overrides(BaseModel):
    # config: dict[str, Any] | None = None
    config: dict[str, Any] = Field(default={})


class Variants(BaseModel):
    # config: dict[str, dict[str, int | float | str]] = Field(default_factory=dict)
    config: dict[str, dict[str, int | float | str]] = Field(default={})


class SimulationRequest(BaseModel):
    @property
    def variant_config_hash(self) -> str:
        """Generate a deep hash of the variant config hash for caching purposes."""
        json = self.model_dump_json(exclude_unset=True, exclude_none=True)
        # Use a consistent hashing function to ensure reproducibility
        return hashlib.md5(json.encode()).hexdigest()  # noqa: S324 insecure hash `md5` is okay for caching


class EcoliSimulationRequest(SimulationRequest):
    """Fits EcoliSim"""

    simulator: SimulatorVersion
    parca_dataset_id: int
    variant_config: dict[str, dict[str, int | float | str]] = Field(
        default={"named_parameters": {"param1": 0.5, "param2": 0.5}}
    )  # TODO: remove this eventually in favor of overrides


class EcoliWorkflowRequest(SimulationRequest):
    """Fits Nextflow workflows

    :param config_id: (str) filename (without '.json') of the given sim config
    :param config_overrides: (Optional[dict[str, Any]]) overrides any key within the file found at {config_id}.json
    """

    config_id: str
    simulator: SimulatorVersion
    overrides: Overrides | None = None
    variants: Variants | None = None
    parca_dataset_id: int | None = None
    # experiment_id: str = Field(default=str(uuid.uuid4()).split("-")[-1])


class AntibioticSimulationRequest(EcoliSimulationRequest):
    antibiotics_config: dict[str, dict[str, int | float | str]] = Field(default_factory=dict)


class EcoliSimulation(BaseModel):
    database_id: int
    sim_request: EcoliSimulationRequest
    slurmjob_id: int | None = None


class EcoliWorkflowSimulation(BaseModel):
    sim_request: EcoliWorkflowRequest
    database_id: int | None = None
    slurmjob_id: int | None = None


class AntibioticSimulation(BaseModel):
    database_id: int
    sim_request: AntibioticSimulationRequest
    slurmjob_id: int | None = None


class EcoliExperiment(BaseModel):
    experiment_id: str
    simulation: EcoliSimulation | EcoliWorkflowSimulation | AntibioticSimulation
    last_updated: str = Field(default_factory=lambda: str(datetime.datetime.now()))
    metadata: Mapping[str, str] = Field(default_factory=dict)
    experiment_tag: str | None = None


class WorkerEvent(BaseModel):
    database_id: int | None = None  # Unique identifier for the worker event (created by the database)
    created_at: str | None = None  # ISO format datetime string (created by the database)
    hpcrun_id: int | None = None  # ID of the HpcRun this event is associated with (known in context of database)

    correlation_id: str  # to correlate with the HpcRun job - see hpc_utils.get_correlation_id()
    sequence_number: int  # Sequence number provided by the message producer (emitter)
    mass: dict[str, float]  # mass from the simulation
    time: float  # Global time of the simulation

    @classmethod
    def from_message_payload(cls, worker_event_message_payload: "WorkerEventMessagePayload") -> "WorkerEvent":
        """Create a WorkerEvent from a WorkerEventMessagePayload."""
        return cls(
            correlation_id=worker_event_message_payload.correlation_id,
            sequence_number=worker_event_message_payload.sequence_number,
            mass=worker_event_message_payload.mass,
            time=worker_event_message_payload.time,
        )


class WorkerEventMessagePayload(BaseModel):
    correlation_id: str  # to correlate with the HpcRun job - see hpc_utils.get_correlation_id()
    sequence_number: int  # Sequence number provided by the message producer (emitter)
    time: float  # global time of the simulation
    mass: dict[str, float]  # Unique identifier for the simulation job
    bulk: list[int] | None  # Bulk data for the simulation (ignored by the database)
    bulk_index: list[str] | None = None  # Labels for the bulk data, if applicable (ignored by the database)


class RequestedObservables(BaseModel):
    items: list[str] = Field(default_factory=list)


@dataclass
class SimulationConfig:
    experiment_id: str | None = None
    sim_data_path: str | None = None
    suffix_time: bool | None = None
    parca_options: dict[str, Any] | None = None  # field(default_factory=dict)
    generations: int | None = None
    n_init_sims: int | None = None
    max_duration: float | None = None
    initial_global_time: float | None = None
    time_step: float | None = None
    single_daughters: bool | None = None
    emitter: str | None = None
    emitter_arg: dict[str, Any] | None = None
    variants: dict[str, Any] | None = None
    analysis_options: dict[str, Any] | None = None
    gcloud: Optional[str] = None
    agent_id: Optional[str] = None
    parallel: Optional[bool] = None
    divide: Optional[bool] = None
    d_period: Optional[bool] = None
    division_threshold: Optional[bool] = None
    division_variable: Optional[list[str]] = None
    chromosome_path: Optional[list[str]] = None
    spatial_environment: Optional[bool] = None
    fixed_media: Optional[str] = None
    condition: Optional[str] = None
    save: Optional[bool] = None
    save_times: Optional[list[str]] = None
    add_processes: Optional[list[str]] = None
    exclude_processes: Optional[list[str]] = None
    profile: Optional[bool] = None
    processes: Optional[list[str]] = None
    process_configs: Optional[dict[str, Any]] = None
    topology: Optional[dict[str, Any]] = None
    engine_process_reports: Optional[list[str]] = None
    emit_paths: Optional[list[str]] = None
    progress_bar: Optional[bool] = None
    emit_topology: Optional[bool] = None
    emit_processes: Optional[bool] = None
    emit_config: Optional[bool] = None
    emit_unique: Optional[bool] = None
    log_updates: Optional[bool] = None
    raw_output: Optional[bool] = None
    description: Optional[str] = None
    seed: Optional[int] = None
    mar_regulon: Optional[bool] = None
    amp_lysis: Optional[bool] = None
    initial_state_file: Optional[str] = None
    skip_baseline: Optional[bool] = None
    daughter_outdir: Optional[str] = None
    lineage_seed: Optional[int] = None
    fail_at_max_duration: Optional[bool] = None
    inherit_from: Optional[list[str]] = None
    spatial_environment_config: Optional[dict[str, Any]] = None
    swap_processes: Optional[dict[str, Any]] = None
    flow: Optional[dict[str, Any]] = None
    initial_state_overrides: Optional[list[str]] = None
    initial_state: Optional[dict[str, Any]] = None

    def to_json(self) -> dict[str, Any]:
        export = {}
        data = asdict(self)
        for attrib, attrib_val in data.items():
            if attrib_val is not None:
                export[attrib] = attrib_val
        return export

    @classmethod
    def from_file(cls, fp: Path) -> "SimulationConfig":
        with open(fp) as f:
            conf = json.load(f)
        return cls(**conf)


class SimulationParameters(FlexData):
    pass
