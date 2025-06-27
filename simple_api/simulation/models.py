import datetime
import hashlib
import json
from enum import StrEnum

from pydantic import BaseModel, Field

from simple_api.common.hpc.sim_utils import read_latest_commit

latest_commit_hash = "96bb7a2"


class JobStatus(StrEnum):
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class HpcRun(BaseModel):
    database_id: int
    slurmjobid: int | None = None  # Slurm job ID if applicable
    status: JobStatus | None = None
    start_time: str | None = None  # ISO format datetime string
    end_time: str | None = None  # ISO format datetime string or None if still running
    error_message: str | None = None  # Error message if the simulation failed


class SimulatorVersion(BaseModel):
    database_id: int  # Unique identifier for the simulator version
    git_commit_hash: str = Field(
        default_factory=read_latest_commit
    )  # Git commit hash for the specific simulator version (first 7 characters)
    git_repo_url: str = "https://github.com/CovertLab/vEcoli"  # Git repository URL for the simulator
    git_branch: str = "master"  # Git branch name for the simulator version


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
    hpc_run: HpcRun | None = None  # HPC run ID if applicable


class EcoliSimulationRequest(BaseModel):
    simulator: SimulatorVersion
    parca_dataset_id: int
    variant_config: dict[str, dict[str, int | float | str]]
    total_time: float = Field(default=11)

    @property
    def variant_config_hash(self) -> str:
        """Generate a deep hash of the variant config hash for caching purposes."""
        json = self.model_dump_json(exclude_unset=True, exclude_none=True)
        # Use a consistent hashing function to ensure reproducibility
        return hashlib.md5(json.encode()).hexdigest()  # noqa: S324 insecure hash `md5` is okay for caching


class EcoliSimulation(BaseModel):
    database_id: int
    sim_request: EcoliSimulationRequest
    hpc_run: HpcRun | None = None  # HPC run ID if applicable


def timestamp() -> str:
    return str(datetime.datetime.now())


class EcoliSimulationRun(BaseModel):
    job_id: int
    simulation: EcoliSimulation
    last_update: str = Field(default_factory=timestamp)
