"""Pydantic models for the compose (process-bigraph) simulation subsystem."""

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
from pydantic import Field

from sms_api.compose.containerization import ContainerizationFileRepr

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FlexData:
    _data: dict[str, Any] = field(default_factory=dict)

    def __init__(self, **kwargs: Any) -> None:
        self._data = kwargs

    def __getattr__(self, item: str) -> Any:
        return self._data[item]

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def keys(self) -> Any:
        return self._data.keys()

    def dict(self) -> dict[str, Any]:
        return self._data


class Payload(FlexData):
    pass


class BaseModel(_BaseModel):
    def as_payload(self) -> Payload:
        serialized = json.loads(self.model_dump_json())
        return Payload(**serialized)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ComposeJobType(enum.Enum):
    SIMULATION = "simulation"
    BUILD_CONTAINER = "build_container"


class PackageType(enum.Enum):
    PYPI = "pypi"
    CONDA = "conda"


class BiGraphComputeType(enum.Enum):
    PROCESS = "process"
    STEP = "step"


class ComposeJobStatus(StrEnum):
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"
    CANCELLED = "cancelled"
    OUT_OF_MEMORY = "out_of_memory"
    SUSPENDED = "suspended"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# HPC job tracking
# ---------------------------------------------------------------------------


class ComposeHpcRun(BaseModel):
    database_id: int
    slurmjobid: int
    correlation_id: str
    job_type: ComposeJobType
    sim_id: int | None
    simulator_id: int | None
    status: ComposeJobStatus | None = None
    start_time: str | None = None
    end_time: str | None = None
    error_message: str | None = None


# ---------------------------------------------------------------------------
# BiGraph compute registry
# ---------------------------------------------------------------------------


class BiGraphComputeOutline(BaseModel):
    module: str
    name: str
    compute_type: BiGraphComputeType
    inputs: str
    outputs: str


class BiGraphCompute(BiGraphComputeOutline):
    database_id: int


class BiGraphProcess(BiGraphCompute):
    pass


class BiGraphStep(BiGraphCompute):
    pass


class PackageOutline(BaseModel):
    package_type: PackageType
    name: str
    compute: list[BiGraphComputeOutline]

    @staticmethod
    def from_pb_outline(pb_outline_json: dict[str, Any], name: str, package_type: PackageType) -> "PackageOutline":
        compute: list[BiGraphComputeOutline] = []
        if "processes" in pb_outline_json:
            for process in pb_outline_json["processes"]:
                compute.append(BiGraphComputeOutline(compute_type=BiGraphComputeType.PROCESS, **process))
        if "steps" in pb_outline_json:
            for step in pb_outline_json["steps"]:
                compute.append(BiGraphComputeOutline(compute_type=BiGraphComputeType.STEP, **step))
        return PackageOutline(package_type=package_type, name=name, compute=compute)


class RegisteredPackage(BaseModel):
    database_id: int
    package_type: PackageType
    name: str
    processes: list[BiGraphProcess]
    steps: list[BiGraphStep]


# ---------------------------------------------------------------------------
# Simulators (container-based)
# ---------------------------------------------------------------------------


class ComposeSimulator(BaseModel):
    singularity_def: ContainerizationFileRepr
    singularity_def_hash: str
    packages: list[RegisteredPackage] | None


class ComposeSimulatorVersion(ComposeSimulator):
    database_id: int
    created_at: datetime.datetime | None = None


class ComposeRegisteredSimulators(BaseModel):
    versions: list[ComposeSimulatorVersion]
    timestamp: datetime.datetime | None = Field(default_factory=datetime.datetime.now)


# ---------------------------------------------------------------------------
# Simulation request / response
# ---------------------------------------------------------------------------


class SimulationFileType(enum.Enum):
    OMEX = "omex"
    PBG = "pbg"
    SBML = "sbml"

    def get_files_suffix(self) -> str:
        return self.value

    @staticmethod
    def get_file_type(suffix: str) -> "SimulationFileType":
        match suffix:
            case ".omex":
                return SimulationFileType.OMEX
            case ".pbg":
                return SimulationFileType.PBG
            case ".sbml":
                return SimulationFileType.SBML
            case _:
                raise ValueError(f"Unknown simulation file type: {suffix}")


class ComposeSimulationRequest(BaseModel):
    request_file_path: Path
    simulation_file_type: SimulationFileType
    end_time_point: float = 1.0
    is_batch: bool


class ComposeSimulationResults(BaseModel):
    path_on_server: Path


class ComposeSimulation(BaseModel):
    database_id: int
    sim_request: ComposeSimulationRequest
    simulator_version: ComposeSimulatorVersion


class ComposeSubmittedSimulation(BaseModel):
    database_id: int
    sim_content: ComposeSimulationResults
    simulator_version: ComposeSimulatorVersion
    hpc_run: ComposeHpcRun | None


class PBAllowList(BaseModel):
    allow_list: list[str]


class ComposeSimulationExperiment(BaseModel):
    simulation_database_id: int
    simulator_database_id: int
    last_updated: str = Field(default_factory=lambda: str(datetime.datetime.now()))
    metadata: Mapping[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Worker events (NATS)
# ---------------------------------------------------------------------------


class ComposeWorkerEvent(BaseModel):
    database_id: int | None = None
    created_at: str | None = None
    hpcrun_id: int | None = None
    correlation_id: str
    sequence_number: int
    mass: dict[str, float]
    time: float

    @classmethod
    def from_message_payload(cls, payload: "ComposeWorkerEventMessagePayload") -> "ComposeWorkerEvent":
        return cls(
            correlation_id=payload.correlation_id,
            sequence_number=payload.sequence_number,
            mass=payload.mass,
            time=payload.time,
        )


class ComposeWorkerEventMessagePayload(BaseModel):
    correlation_id: str
    sequence_number: int
    time: float
    mass: dict[str, float]


# ---------------------------------------------------------------------------
# Package registration models (todo:57)
# ---------------------------------------------------------------------------


class PackageRegistrationRequest(BaseModel):
    kind: str = Field(description="'repo_url', 'local_path', or 'outline'")
    url: str | None = Field(default=None, description="Git repo URL (required when kind='repo_url')")
    ref: str | None = Field(default=None, description="Git branch/tag/commit (optional)")
    path: str | None = Field(default=None, description="Local path (required when kind='local_path')")
    outline: PackageOutline | None = Field(default=None, description="Inline outline (required when kind='outline')")


class PackageAuditRequest(BaseModel):
    target: str = Field(description="Git repo URL or local filesystem path")
    ref: str | None = Field(default=None, description="Git branch/tag/commit (optional)")
    run_install: bool = Field(default=False, description="Run pip install smoke test")


class AuditCheckResult(BaseModel):
    name: str
    status: str
    detail: str = ""


class PackageAuditResult(BaseModel):
    target: str
    checks: list[AuditCheckResult]
    fixes: list[str]
    summary: str = ""


class PackageListing(BaseModel):
    id: int
    name: str
    package_type: PackageType
    num_processes: int
    num_steps: int
    created_at: str | None = None


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


class BiomodelSimulator(str, enum.Enum):
    COPASI = "copasi"
    TELLURIUM = "tellurium"


class BiomodelInfo(BaseModel):
    biomodel_id: str
    metadata: dict[str, Any]


class BiomodelsRunRequest(BaseModel):
    model_ids: list[str] | None = Field(
        default=None, description="Specific BioModel IDs to run. Mutually exclusive with n_models."
    )
    n_models: int | None = Field(
        default=None, ge=1, le=50, description="Run the first N BioModels. Ignored if model_ids is set."
    )
    simulator: BiomodelSimulator = Field(
        default=BiomodelSimulator.COPASI, description="Simulator to use for each model."
    )


class BiomodelsRunResult(BaseModel):
    submitted: list[ComposeSimulationExperiment]
    failed: list[str] = Field(default_factory=list, description="BioModel IDs that failed to submit.")


class BiomodelsAuditRequest(BaseModel):
    biomodel_id: str
    simulators: list[BiomodelSimulator] = Field(
        default_factory=lambda: [BiomodelSimulator.COPASI, BiomodelSimulator.TELLURIUM]
    )


class BiomodelsAuditResult(BaseModel):
    experiment: ComposeSimulationExperiment
    simulators_used: list[BiomodelSimulator]


class BiomodelsRegressionRequest(BaseModel):
    n_models: int = Field(default=10, ge=1, le=1000, description="Number of models to run. Ignored if model_ids set.")
    model_ids: list[str] | None = Field(default=None, description="Specific BioModel IDs to run. Overrides n_models.")
    simulators: list[BiomodelSimulator] = Field(
        default_factory=lambda: [BiomodelSimulator.COPASI, BiomodelSimulator.TELLURIUM],
        description="Simulators to wire into each model's PB document.",
    )


class BiomodelsRegressionResult(BaseModel):
    submitted: list[ComposeSimulationExperiment]
    failed: list[str] = Field(default_factory=list, description="BioModel IDs that failed to submit.")
    total_requested: int


def get_singularity_hash(singularity_def_rep: ContainerizationFileRepr) -> str:
    return hashlib.md5(singularity_def_rep.representation.encode("utf-8")).hexdigest()  # noqa: S324


# ---------------------------------------------------------------------------
# Rest-process runtime models
# ---------------------------------------------------------------------------


class ProcessInitializeRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict, description="Config dict matching the process config_schema.")


class ProcessInstance(BaseModel):
    process_id: str = Field(description="UUID of the instantiated process.")
    process_name: str = Field(description="Name of the process class that was instantiated.")


class ProcessUpdateRequest(BaseModel):
    state: dict[str, Any] = Field(default_factory=dict, description="Current state to pass to process.update().")
    interval: float = Field(default=1.0, ge=0.0, description="Time interval for this update step.")


# ---------------------------------------------------------------------------
# Process registry persistence models
# ---------------------------------------------------------------------------


class ProcessInstanceStatus(str, enum.Enum):
    ACTIVE = "active"
    ENDED = "ended"


class ProcessInstanceRecord(BaseModel):
    database_id: int
    process_id: str
    process_name: str
    config: dict[str, Any]
    status: ProcessInstanceStatus
    created_at: str
    ended_at: str | None = None


class ProcessUpdateRecord(BaseModel):
    database_id: int
    process_instance_id: int
    interval: float
    state: dict[str, Any]
    result: dict[str, Any] | None
    called_at: str


# ---------------------------------------------------------------------------
# PBG Wrapper models
# ---------------------------------------------------------------------------


class WrapperStatus(StrEnum):
    GENERATING = "generating"
    STORING = "storing"
    READY = "ready"
    BUILDING = "building"
    AVAILABLE = "available"
    FAILED = "failed"


class PbgPortSchema(BaseModel):
    """A single port definition for a PBG Process/Step."""

    name: str = Field(..., description="Port name, e.g. 'substrate'")
    schema_expr: str = Field(..., description="Bigraph-schema type expression, e.g. 'float' or 'map[string,float]'")
    description: str | None = Field(default=None, description="Human-readable description of the port")


class PbgConfigParam(BaseModel):
    """A single config parameter for a PBG Process/Step."""

    name: str = Field(..., description="Parameter name, e.g. 'rate'")
    type: str = Field(default="float", description="Bigraph-schema type, e.g. 'float' or 'string'")
    default: str | float | int | bool | None = Field(default=None, description="Default value")
    description: str | None = Field(default=None, description="Human-readable description")


class PbgWrapperCreateRequest(BaseModel):
    source_repo_url: str = Field(
        ..., description="GitHub URL of the simulator to wrap, e.g. https://github.com/vivarium-collective/mem3dg"
    )
    source_ref: str = Field(default="main", description="Git branch/tag/commit to target")
    tool_name: str | None = Field(
        default=None, description="Override the derived tool name (default: inferred from repo name)"
    )
    extra_instructions: str | None = Field(default=None, description="Optional extra context for the wrapper agent")
    # LLM-free scaffold fields — used when use_agent=False or no API key is configured.
    process_type: str = Field(
        default="Process",
        description="'Process' (time-stepped) or 'Step' (event-driven/stateless)",
    )
    input_ports: list[PbgPortSchema] = Field(
        default_factory=list,
        description="Input port definitions for the scaffold path (unused when use_agent=True)",
    )
    output_ports: list[PbgPortSchema] = Field(
        default_factory=list,
        description="Output port definitions for the scaffold path (unused when use_agent=True)",
    )
    config_params: list[PbgConfigParam] = Field(
        default_factory=list,
        description="Config parameter definitions for the scaffold path (unused when use_agent=True)",
    )
    use_agent: bool = Field(
        default=True,
        description=(
            "When True (default), invoke the Claude API pbg-expert agent to generate the wrapper. "
            "When False (or when COMPOSE_PBG_ANTHROPIC_API_KEY is not configured), fall back to "
            "deterministic template-based scaffolding using the port/config definitions above."
        ),
    )


class PbgWrapperRecord(BaseModel):
    wrapper_id: int
    tool_name: str
    source_repo_url: str
    source_ref: str
    status: WrapperStatus
    simulator_id: int | None = None
    storage_uri: str | None = None
    error_message: str | None = None
    created_at: str
