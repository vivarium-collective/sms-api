import hashlib
from enum import StrEnum

from pydantic import BaseModel


class ParcaDataset(BaseModel):
    id: str  # Unique identifier for the dataset
    name: str  # Name of the dataset
    remote_archive_path: str  # Path to the dataset archive in remote storage
    description: str | None = None  # Optional description of the dataset
    hash: str  # Hash of the dataset for integrity verification


class VariantSpec(BaseModel):
    variant_id: str  # Unique identifier for the variant
    name: str  # Name of the variant
    description: str | None = None  # Optional description of the variant
    parameters: dict[str, float]  # Parameters specific to the variant, e.g., growth rate, yield coefficients


class SimulationSpec(BaseModel):
    parca_dataset: ParcaDataset
    variant_spec: VariantSpec
    named_parameters: dict[str, float]  # Named parameters for the simulation


class EcoliSimulationRequest(BaseModel):
    simulation_spec: SimulationSpec  # Parameters for the simulation
    simulator_version: str

    @property
    def deep_hash(self) -> str:
        """Generate a deep hash of the simulation request for caching purposes."""
        json = self.model_dump_json(exclude_unset=True, exclude_none=True)
        # Use a consistent hashing function to ensure reproducibility
        return hashlib.md5(json.encode()).hexdigest()


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


class EcoliSimulation(BaseModel):
    database_id: str
    sim_request: EcoliSimulationRequest
    slurm_job_id: int | None = None  # Slurm job ID if applicable
    status: JobStatus | None = None
    start_time: str | None = None  # ISO format datetime string
    end_time: str | None = None  # ISO format datetime string or None if still running
    error_message: str | None = None  # Error message if the simulation failed
