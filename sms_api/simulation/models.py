import datetime
import enum
import hashlib
import json
from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, Field


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
    job_type: JobType
    ref_id: int  # primary key of the object this HPC run is associated with (sim, parca, etc.)
    status: JobStatus | None = None
    start_time: str | None = None  # ISO format datetime string
    end_time: str | None = None  # ISO format datetime string or None if still running
    error_message: str | None = None  # Error message if the simulation failed


class Simulator(BaseModel):
    git_commit_hash: str  # Git commit hash for the specific simulator version (first 7 characters)
    git_repo_url: str = Field(
        default="https://github.com/vivarium-collective/vEcoli"
    )  # Git repository URL for the simulator
    git_branch: str = Field(default="messages")  # Git branch name for the simulator version


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


class EcoliSimulationRequest(BaseModel):
    simulator: SimulatorVersion
    parca_dataset_id: int
    variant_config: dict[str, dict[str, int | float | str]]

    @property
    def variant_config_hash(self) -> str:
        """Generate a deep hash of the variant config hash for caching purposes."""
        json = self.model_dump_json(exclude_unset=True, exclude_none=True)
        # Use a consistent hashing function to ensure reproducibility
        return hashlib.md5(json.encode()).hexdigest()  # noqa: S324 insecure hash `md5` is okay for caching


class AntibioticSimulationRequest(EcoliSimulationRequest):
    antibiotics_config: dict[str, dict[str, int | float | str]] = Field(default_factory=dict)


class EcoliSimulation(BaseModel):
    database_id: int
    sim_request: EcoliSimulationRequest
    slurmjob_id: int | None = None


class AntibioticSimulation(EcoliSimulation):
    sim_request: AntibioticSimulationRequest


class EcoliExperiment(BaseModel):
    experiment_id: str
    simulation: EcoliSimulation | AntibioticSimulation
    last_updated: str = Field(default_factory=lambda: str(datetime.datetime.now()))
    metadata: Mapping[str, str] = Field(default_factory=dict)


class WorkerEvent(BaseModel):
    database_id: int | None = None  # Unique identifier for the worker event (created by the database)
    created_at: str | None = None  # ISO format datetime string (created by the database)
    hpcrun_id: int  # Unique identifier for the simulation job
    sequence_number: int  # Sequence number provided by the message producer (emitter)
    sim_data: list[tuple[str, str, float]]  # Simulation data with label/path/value
    global_time: float | None = None  # Global time of the simulation, if applicable
    error_message: str | None = None


class RequestedObservables(BaseModel):
    items: list[str] = Field(default_factory=list)
