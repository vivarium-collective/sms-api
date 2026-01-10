import datetime
import enum
import hashlib
import json
from dataclasses import field
from typing import Any

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, Field

from sms_api.common.models import JobStatus
from sms_api.config import get_settings


class BaseModel(_BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)


def trim_attributes(cls: BaseModel, excluded: list[str] | None = None) -> None:
    if excluded is None:
        excluded = []
    for attrname in list(cls.model_fields.keys()):
        attr = getattr(cls, attrname)
        if attr is None and attrname not in excluded:
            delattr(cls, attrname)
        if isinstance(attr, (list, dict)) and not len(attr):
            delattr(cls, attrname)


class JobType(enum.Enum):
    ANALYSIS = "analysis"
    SIMULATION = "simulation"
    PARCA = "parca"
    BUILD_IMAGE = "build_image"


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
    id: int
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


class ParcaOptions(BaseModel):
    cpus: int = 3
    outdir: str = str(get_settings().simulation_outdir)
    operons: bool = True
    ribosome_fitting: bool = True
    remove_rrna_operons: bool = False
    remove_rrff: bool = False
    stable_rrna: bool = False
    new_genes: str = "off"
    debug_parca: bool = False
    load_intermediate: str | None = None
    save_intermediates: bool = False
    intermediates_directory: str = ""
    variable_elongation_transcription: bool = True
    variable_elongation_translation: bool = False

    def model_post_init(self, context: Any, /) -> None:
        trim_attributes(self)


class ParcaDatasetRequest(BaseModel):
    simulator_version: SimulatorVersion  # Version of the software used to generate the dataset
    parca_config: ParcaOptions = ParcaOptions()

    @property
    def config_hash(self) -> str:
        """Generate a deep hash of the parca request for caching purposes."""
        json_str = json.dumps(self.parca_config.model_dump())
        return hashlib.md5(json_str.encode()).hexdigest()  # noqa: S324 insecure hash `md5` is okay for caching


class ParcaDataset(BaseModel):
    database_id: int  # Unique identifier for the dataset
    parca_dataset_request: ParcaDatasetRequest  # Request parameters for the dataset
    remote_archive_path: str | None = None  # Path to the dataset archive in remote storage


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


class AnalysisOptions(BaseModel):
    cpus: int = 3
    single: dict[str, Any] | None = None
    multidaughter: dict[str, Any] | None = None
    multigeneration: dict[str, dict[str, Any]] | None = None
    multiseed: dict[str, dict[str, Any]] | None = None
    multivariant: dict[str, dict[str, Any]] | None = None
    multiexperiment: dict[str, Any] | None = None

    def model_post_init(self, context: Any, /) -> None:
        trim_attributes(self)


class SimulationConfig(BaseModel):
    experiment_id: str
    parca_options: ParcaOptions = ParcaOptions()
    analysis_options: AnalysisOptions = AnalysisOptions()
    sim_data_path: str | None = None
    suffix_time: bool = False
    generations: int = 1
    n_init_sims: int = 1
    max_duration: float = 10800.0
    initial_global_time: float = 0.0
    time_step: float = 1.0
    single_daughters: bool = True
    emitter: str = "parquet"
    emitter_arg: dict[str, str] = Field(
        default_factory=lambda: {"out_dir": str(get_settings().simulation_outdir)}
    )  # str(get_settings().hpc_sim_base_path)
    variants: dict[str, dict[str, dict[str, list[float | str | int]]]] = Field(default={})
    gcloud: str | None = None
    agent_id: str | None = None
    parallel: bool | None = None
    divide: bool | None = None
    d_period: bool | None = None
    division_threshold: bool | None = None
    division_variable: list[str] = Field(default=[])
    chromosome_path: list[str] | None = None
    spatial_environment: bool | None = None
    fixed_media: str | None = None
    condition: str | None = None
    save: bool | None = None
    save_times: list[str] = Field(default=[])
    add_processes: list[str] = Field(default=[])
    exclude_processes: list[str] = Field(default=[])
    profile: bool | None = None
    processes: list[str] = Field(default=[])
    process_configs: dict[str, Any] = Field(default={})
    topology: dict[str, Any] = field(default={})
    engine_process_reports: list[list[str]] = Field(default=[])
    emit_paths: list[str] = Field(default=[])
    progress_bar: bool | None = None
    emit_topology: bool | None = None
    emit_processes: bool | None = None
    emit_config: bool | None = None
    emit_unique: bool | None = None
    log_updates: bool | None = None
    raw_output: bool | None = None
    description: str | None = None
    seed: int | None = None
    mar_regulon: bool | None = None
    amp_lysis: bool | None = None
    initial_state_file: str | None = None
    skip_baseline: bool | None = None
    daughter_outdir: str | None = None
    lineage_seed: int | None = None
    fail_at_max_duration: bool | None = None
    inherit_from: list[str] = Field(default=[])
    spatial_environment_config: dict[str, Any] = Field(default={})
    swap_processes: dict[str, Any] = Field(default={})
    flow: dict[str, Any] = Field(default={})
    initial_state_overrides: list[str] = Field(default=[])
    initial_state: dict[str, Any] = Field(default={})

    def model_post_init(self, *args: Any) -> None:
        for attrname in list(SimulationConfig.model_fields.keys()):
            attr = getattr(self, attrname)
            if (attr is None and attrname != "sim_data_path") or (attr == ["string"]):
                delattr(self, attrname)
            if isinstance(attr, (list, dict)) and not len(attr):
                delattr(self, attrname)


class ExperimentRequest(BaseModel):
    """Used by the /simulation endpoint."""

    experiment_id: str
    simulation_name: str | None = None
    metadata: dict[str, Any] = {}
    run_parca: bool = True
    generations: int = 2
    n_init_sims: int = 1
    lineage_seed: int = 3
    max_duration: float = 10800.0
    initial_global_time: float = 0.0
    time_step: float = 1.0
    single_daughters: bool = True
    variants: dict[str, dict[str, dict[str, list[float | str | int]]]] = Field(default={})
    analysis_options: dict[str, Any] = Field(default={})
    gcloud: str | None = None
    agent_id: str | None = None
    parallel: bool | None = None
    divide: bool | None = None
    d_period: bool | None = None
    division_threshold: bool | None = None
    division_variable: list[str] = Field(default=[])
    chromosome_path: list[str] | None = None
    spatial_environment: bool | None = None
    fixed_media: str | None = None
    condition: str | None = None
    add_processes: list[str] = Field(default=[])
    exclude_processes: list[str] = Field(default=[])
    profile: bool | None = None
    processes: list[str] = Field(default=[])
    process_configs: dict[str, Any] = Field(default={})
    topology: dict[str, Any] = field(default={})
    engine_process_reports: list[list[str]] = Field(default=[])
    emit_paths: list[str] = Field(default=[])
    emit_topology: bool | None = None
    emit_processes: bool | None = None
    emit_config: bool | None = None
    emit_unique: bool | None = None
    log_updates: bool | None = None
    description: str | None = None
    seed: int | None = None
    mar_regulon: bool | None = None
    amp_lysis: bool | None = None
    initial_state_file: str | None = None
    skip_baseline: bool | None = None
    fail_at_max_duration: bool | None = None
    inherit_from: list[str] = Field(default=[])
    spatial_environment_config: dict[str, Any] = Field(default={})
    swap_processes: dict[str, Any] = Field(default={})
    flow: dict[str, Any] = Field(default={})
    initial_state_overrides: list[str] = Field(default=[])
    initial_state: dict[str, Any] = Field(default={})

    def model_post_init(self, context: Any, /) -> None:
        if self.simulation_name is None:
            self.simulation_name = self.experiment_id

    def to_config(self) -> SimulationConfig:
        attributes = self.model_json_schema()["properties"]
        excluded = ["simdata_id", "metadata"]
        config_kwargs = {}
        for attribute in attributes:
            if attribute not in excluded:
                attr_val = getattr(self, attribute)
                if attr_val != "string":
                    config_kwargs[attribute] = attr_val

        # config_kwargs = {attribute: getattr(self, attribute) for attribute in attributes if attribute not in excluded}

        return SimulationConfig(**config_kwargs)


class SimulationRequest(BaseModel):
    """Used by the /simulation endpoint."""

    config: SimulationConfig
    simulator: Simulator | None = None
    simulator_id: int | None = None
    parca_dataset_id: int | None = None

    def model_post_init(self, context: Any, /) -> None:
        if self.simulator is None and self.simulator_id is None:
            raise ValueError(
                "You must specify either a Simulator (hash, branch, url) OR the db id of an already-inserted simulation"
            )


class Simulation(BaseModel):
    """Used by the /simulation endpoint"""

    database_id: int
    simulator_id: int
    parca_dataset_id: int
    config: SimulationConfig
    last_updated: str = Field(default=str(datetime.datetime.now()))
    job_id: int | None = None
