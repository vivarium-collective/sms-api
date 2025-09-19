import datetime
import enum
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel as _BaseModel
from pydantic import Field, model_validator

from sms_api.config import get_settings

BASE_SIMULATION_CONFIG_PATH = Path("assets/sms_base_simulation_config.json")


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


class ParcaOptions(BaseModel):
    cpus: int = 2
    outdir: str = ""
    operons: bool = True
    ribosome_fitting: bool = True
    rnapoly_fitting: bool = True
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


AnalysisOptions: type = list[dict[str, dict[str, int | Any]]]


class VariantOpType(StrEnum):
    CARTESIAN = "prod"
    ZIPPED = "zip"


class VariantParameter(BaseModel):
    # like: "method": {"value": ["multiplicative"]},, where method is name and value is method.value.value()
    name: str
    value: list[str | float | int]


class Variant(BaseModel):
    module_name: str
    parameters: list[VariantParameter]
    op: VariantOpType = VariantOpType.CARTESIAN


class VariantConfig(BaseModel):
    variants: list[Variant] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = {}
        for variant in self.variants:
            data[variant.module_name] = {param.name: {"value": param.value} for param in variant.parameters}
            data[variant.module_name]["op"] = variant.op  # type: ignore[assignment]
        return data


class EmitterArg(BaseModel):
    out_dir: str


class SimulationConfig(BaseModel):
    experiment_id: str | None = None
    sim_data_path: str | None = None
    suffix_time: bool = False
    parca_options: dict[str, bool | int | str | None | Any] = Field(default_factory=dict)
    generations: int = 1
    n_init_sims: int | None = None
    max_duration: float = 10800.0
    initial_global_time: float = 0.0
    time_step: float = 1.0
    single_daughters: bool = True
    emitter: str = "parquet"
    emitter_arg: dict[str, str] = Field(default_factory=dict)
    variants: dict[str, dict[str, dict[str, list[float | str | int]]]] = Field(default_factory=dict)
    analysis_options: dict[str, Any] = Field(default_factory=dict)
    gcloud: str | None = None
    agent_id: str | None = None
    parallel: bool | None = None
    divide: bool | None = None
    d_period: bool | None = None
    division_threshold: bool | None = None
    division_variable: list[str] = Field(default_factory=list)
    chromosome_path: list[str] | None = None
    spatial_environment: bool | None = None
    fixed_media: str | None = None
    condition: str | None = None
    save: bool | None = None
    save_times: list[str] = Field(default_factory=list)
    add_processes: list[str] = Field(default_factory=list)
    exclude_processes: list[str] = Field(default_factory=list)
    profile: bool | None = None
    processes: list[str] = Field(default_factory=list)
    process_configs: dict[str, Any] = Field(default_factory=dict)
    topology: dict[str, Any] = field(default_factory=dict)
    engine_process_reports: list[list[str]] = Field(default_factory=list)
    emit_paths: list[str] = Field(default_factory=list)
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
    inherit_from: list[str] = Field(default_factory=list)
    spatial_environment_config: dict[str, Any] = Field(default_factory=dict)
    swap_processes: dict[str, Any] = Field(default_factory=dict)
    flow: dict[str, Any] = Field(default_factory=dict)
    initial_state_overrides: list[str] = Field(default_factory=list)
    initial_state: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, fp: Path, config_id: str | None = None) -> "SimulationConfig":
        filepath = fp
        with open(filepath) as f:
            conf = json.load(f)
        return cls(**conf)

    @classmethod
    def from_base(cls) -> "SimulationConfig":
        return cls.from_file(fp=BASE_SIMULATION_CONFIG_PATH)

    @model_validator(mode="after")
    def set_outdirs(self) -> "SimulationConfig":
        env = get_settings()
        self.emitter_arg = {"out_dir": env.simulation_outdir}
        self.daughter_outdir = env.simulation_outdir
        self.parca_options = {"cpus": 2}
        return self


class SimulationConfiguration(SimulationConfig):
    pass


class ConfigOverrides(SimulationConfig):
    pass


class UploadedConfig(BaseModel):
    id: str
    data: dict[str, Any] = Field(default_factory=dict)


class UploadedSimulationConfig(BaseModel):
    config_id: str
    # data: SimulationConfiguration


class UploadedAnalysisConfig(BaseModel):
    config_id: str


class EcoliExperimentRequestDTO(BaseModel):
    config_id: str
    overrides: ConfigOverrides | None = None
    # parca_dataset_id: int | None = None  TODO: we should pin this down and change only administratively
    # simulator: SimulatorVersion  TODO: we should pin this down and change only administratively


class EcoliExperimentDTO(BaseModel):
    experiment_id: str
    request: EcoliExperimentRequestDTO
    last_updated: str = Field(default_factory=lambda: str(datetime.datetime.now()))
    metadata: Mapping[str, str] = Field(default_factory=dict)
    experiment_tag: str | None = None
    # simulation: EcoliSimulation | EcoliWorkflowSimulation | AntibioticSimulation
