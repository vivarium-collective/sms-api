from enum import StrEnum

from pydantic import BaseModel

# class ParcaDataset(BaseModel):
#     id: str
#     name: str
#     remote_archive_path: str
#     description: str | None = None
#     hash: str


class Parameters(BaseModel):
    named_parameters: dict[str, float]  # Named parameters for the simulation


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"


class EcoliSimulationRequest(BaseModel):
    parameters: Parameters  # Parameters for the simulation


class EcoliSimulation(BaseModel):
    database_id: str
    sim_request: EcoliSimulationRequest
    slurm_job_id: int | None = None  # Slurm job ID if applicable
    status: JobStatus | None = None
    start_time: str | None = None  # ISO format datetime string
    end_time: str | None = None  # ISO format datetime string or None if still running
    error_message: str | None = None  # Error message if the simulation failed
