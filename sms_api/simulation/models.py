import hashlib
from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"
    NOT_SUBMITTED = "not_submitted"


class SimulatorVersion(BaseModel):
    id: str  # Unique identifier for the simulator version
    version: str  # displayed version
    docker_image: str  # Docker image for the simulator version
    docker_hash: str  # Optional Docker image hash for integrity verification


class ParcaDatasetRequest(BaseModel):
    simulator_version: SimulatorVersion  # Version of the software used to generate the dataset
    is_default: bool = False  # Whether this is a default dataset

    @property
    def deep_hash(self) -> str:
        """Generate a deep hash of the simulation request for caching purposes."""
        json = self.model_dump_json(exclude_unset=True, exclude_none=True)
        # Use a consistent hashing function to ensure reproducibility
        return hashlib.md5(json.encode()).hexdigest()  # noqa: S324 insecure hash `md5` is okay for caching


class ParcaDataset(BaseModel):
    id: str  # Unique identifier for the dataset
    parca_dataset_request: ParcaDatasetRequest  # Request parameters for the dataset
    remote_archive_path: str  # Path to the dataset archive in remote storage
    job_status: JobStatus
    error_message: str | None = None  # Error message if the dataset generation failed


class VariantSpec(BaseModel):
    variant_id: str  # Unique identifier for the variant
    name: str  # Name of the variant
    description: str | None = None  # Optional description of the variant
    parameters: dict[str, float]  # Parameters specific to the variant, e.g., growth rate, yield coefficients


class SimulationSpec(BaseModel):
    parca_dataset: ParcaDataset
    variant_spec: VariantSpec


class EcoliSimulationRequest(BaseModel):
    simulation_spec: SimulationSpec  # Parameters for the simulation
    simulator_version: SimulatorVersion

    @property
    def deep_hash(self) -> str:
        """Generate a deep hash of the simulation request for caching purposes."""
        json = self.model_dump_json(exclude_unset=True, exclude_none=True)
        # Use a consistent hashing function to ensure reproducibility
        return hashlib.md5(json.encode()).hexdigest()  # noqa: S324 insecure hash `md5` is okay for caching


class EcoliSimulation(BaseModel):
    database_id: str
    sim_request: EcoliSimulationRequest
    slurm_job_id: int | None = None  # Slurm job ID if applicable
    status: JobStatus | None = None
    start_time: str | None = None  # ISO format datetime string
    end_time: str | None = None  # ISO format datetime string or None if still running
    error_message: str | None = None  # Error message if the simulation failed
