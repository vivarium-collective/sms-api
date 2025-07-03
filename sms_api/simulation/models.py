import datetime
import enum
import hashlib
import json
from enum import StrEnum
import os
from pathlib import Path

import dotenv
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


class SimulatorVersion(BaseModel):
    database_id: int  # Unique identifier for the simulator version
    git_commit_hash: str  # Git commit hash for the specific simulator version (first 7 characters)
    git_repo_url: str  # Git repository URL for the simulator
    git_branch: str  # Git branch name for the simulator version


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


class EcoliSimulation(BaseModel):
    database_id: int
    sim_request: EcoliSimulationRequest


class WorkerEvent(BaseModel):
    database_id: int | None = None  # Unique identifier for the worker event (created by the database)
    created_at: str | None = None  # ISO format datetime string (created by the database)
    hpcrun_id: int  # Unique identifier for the simulation job
    sequence_number: int  # Sequence number provided by the message producer (emitter)
    sim_data: list[tuple[str, str, float]]  # Simulation data with label/path/value
    global_time: float | None = None  # Global time of the simulation, if applicable
    error_message: str | None = None


class EcoliSimulationRun(BaseModel):
    job_id: int
    simulation: EcoliSimulation
    last_update: str = Field(default_factory=lambda: str(datetime.datetime.now()))


class ServerModes(StrEnum):
    DEV = "http://localhost:8000"
    PROD = "https://sms.cam.uchc.edu"

    @classmethod
    def detect(cls, env_path: Path) -> str:
        return cls.DEV if dotenv.load_dotenv(env_path) else cls.PROD


class ServiceTypes(StrEnum):
    SIMULATION = "simulation"
    MONGO = "mongo"
    POSTGRES = "postgres"
    AUTH = "auth"


class ServicePing(BaseModel):
    service_type: ServiceTypes
    dialect_name: str
    dialect_driver: str


class Namespaces(StrEnum):
    DEVELOPMENT = "dev"
    PRODUCTION = "prod"
    TEST = "test"
