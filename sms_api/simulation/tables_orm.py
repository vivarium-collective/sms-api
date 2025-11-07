import datetime
import enum
import logging
from typing import Any, Optional

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sms_api.data.models import AnalysisConfig, AnalysisConfigOptions, ExperimentAnalysisDTO
from sms_api.simulation.models import (
    EcoliSimulationDTO,
    ExperimentMetadata,
    HpcRun,
    JobStatus,
    JobType,
    SimulationConfig,
    SimulatorVersion,
    WorkerEvent,
)

logger = logging.getLogger(__name__)


class JobStatusDB(enum.Enum):
    WAITING = "waiting"
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def to_job_status(self) -> JobStatus:
        return JobStatus(self.value)


class JobTypeDB(enum.Enum):
    SIMULATION = "simulation"
    PARCA = "parca"
    BUILD_IMAGE = "build_image"

    def to_job_type(self) -> JobType:
        return JobType(self.value)

    @classmethod
    def from_job_type(cls, job_type: JobType) -> "JobTypeDB":
        return JobTypeDB(job_type.value)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class ORMSimulator(Base):
    __tablename__ = "simulator"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    git_repo_url: Mapped[str] = mapped_column(nullable=False)
    git_branch: Mapped[str] = mapped_column(nullable=False)
    git_commit_hash: Mapped[str] = mapped_column(nullable=False)  # first 7 characters of the commit hash

    def to_simulator_version(self) -> SimulatorVersion:
        return SimulatorVersion(
            database_id=self.id,
            created_at=self.created_at,
            git_repo_url=self.git_repo_url,
            git_branch=self.git_branch,
            git_commit_hash=self.git_commit_hash,
        )


class ORMHpcRun(Base):
    __tablename__ = "hpcrun"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    job_type: Mapped[JobTypeDB] = mapped_column(nullable=False)
    correlation_id: Mapped[str] = mapped_column(nullable=False, index=True)
    slurmjobid: Mapped[int] = mapped_column(nullable=True)
    start_time: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    end_time: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    status: Mapped[JobStatusDB] = mapped_column(nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(nullable=True)
    jobref_simulation_id: Mapped[Optional[int]] = mapped_column(ForeignKey("simulation.id"), nullable=True, index=True)
    jobref_parca_dataset_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("parca_dataset.id"), nullable=True, index=True
    )
    jobref_simulator_id: Mapped[Optional[int]] = mapped_column(ForeignKey("simulator.id"), nullable=True, index=True)

    def to_hpc_run(self) -> HpcRun:
        ref_id = self.jobref_simulation_id or self.jobref_parca_dataset_id or self.jobref_simulator_id
        if ref_id is None:
            raise RuntimeError("ORMHpcRun must have at least one job reference set.")
        return HpcRun(
            database_id=self.id,
            slurmjobid=self.slurmjobid,
            correlation_id=self.correlation_id,
            job_type=self.job_type.to_job_type(),
            ref_id=ref_id,
            status=self.status.to_job_status(),
            error_message=self.error_message,
            start_time=str(self.start_time) if self.start_time else None,
            end_time=str(self.end_time) if self.end_time else None,
        )


class ORMParcaDataset(Base):
    __tablename__ = "parca_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    simulator_id: Mapped[int] = mapped_column(ForeignKey("simulator.id"), nullable=False, index=True)
    parca_config: Mapped[dict[str, int | float | str]] = mapped_column(JSONB, nullable=False)
    parca_config_hash: Mapped[str] = mapped_column(nullable=False)
    remote_archive_path: Mapped[Optional[str]] = mapped_column(nullable=True)


class ORMSimulation(Base):
    __tablename__ = "simulation"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    simulator_id: Mapped[int] = mapped_column(ForeignKey("simulator.id"), nullable=False, index=True)
    parca_dataset_id: Mapped[int] = mapped_column(ForeignKey("parca_dataset.id"), nullable=False, index=True)
    variant_config: Mapped[dict[str, dict[str, int | float | str]]] = mapped_column(JSONB, nullable=False)
    variant_config_hash: Mapped[str] = mapped_column(nullable=False)


class ORMWorkerEvent(Base):
    __tablename__ = "worker_event"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    correlation_id: Mapped[str] = mapped_column(nullable=False, index=True)
    sequence_number: Mapped[int] = mapped_column(nullable=False, index=True)
    mass: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False)
    bulk: Mapped[Optional[list[int]]] = mapped_column(JSONB, nullable=True)
    bulk_index: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True)
    time: Mapped[float] = mapped_column(nullable=True)
    hpcrun_id: Mapped[int] = mapped_column(ForeignKey("hpcrun.id"), nullable=False, index=True)

    @classmethod
    def from_worker_event(cls, worker_event: "WorkerEvent", hpcrun_id: int) -> "ORMWorkerEvent":
        return cls(
            # database_id=self.id,                 # populated in the database
            # created_at=str(self.created_at),     # populated in the database
            hpcrun_id=hpcrun_id,
            correlation_id=worker_event.correlation_id,
            sequence_number=worker_event.sequence_number,
            mass=worker_event.mass,
            bulk=None,
            bulk_index=None,
            time=worker_event.time,
        )

    def to_worker_event(self) -> WorkerEvent:
        return WorkerEvent(
            database_id=self.id,
            created_at=str(self.created_at),
            hpcrun_id=self.hpcrun_id,
            correlation_id=self.correlation_id,
            sequence_number=self.sequence_number,
            mass=self.mass,
            time=self.time,
        )

    @staticmethod
    def from_query_results(record: tuple[dict[str, float], int, int, float, int]) -> WorkerEvent:
        mass_data, sequence_number, record_id, event_time, hpcrun_id = record

        # ORMWorkerEvent.mass, ORMWorkerEvent.sequence_number, ORMWorkerEvent.id, ORMWorkerEvent.time
        return WorkerEvent(
            database_id=record_id,
            correlation_id="",
            sequence_number=sequence_number,
            mass=mass_data,
            time=event_time,
            hpcrun_id=hpcrun_id,
        )


class ORMAnalysis(Base):
    """Used by the /ecoli router"""

    __tablename__ = "analysis"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)  # this should be request.analysis_name
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    last_updated: Mapped[str] = mapped_column(nullable=False)
    job_name: Mapped[str] = mapped_column(nullable=True)
    job_id: Mapped[int] = mapped_column(nullable=True)

    def to_dto(self) -> ExperimentAnalysisDTO:
        options = AnalysisConfigOptions(**self.config["analysis_options"])
        emitter_arg = self.config["emitter_arg"]
        config_dto = AnalysisConfig(analysis_options=options, emitter_arg=emitter_arg)
        return ExperimentAnalysisDTO(
            database_id=self.id,
            name=self.name,
            config=config_dto,
            last_updated=self.last_updated,
            job_name=self.job_name,
            job_id=self.job_id,
        )


class ORMExperiment(Base):
    """Used by the /ecoli router"""

    __tablename__ = "ecoli_experiment"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    last_updated: Mapped[str] = mapped_column(nullable=False)
    job_name: Mapped[str] = mapped_column(nullable=True)
    job_id: Mapped[int] = mapped_column(nullable=True)
    experiment_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=True)

    def to_dto(self) -> EcoliSimulationDTO:
        config_dto = SimulationConfig(**self.config)
        metadata = ExperimentMetadata(root=self.experiment_metadata)
        return EcoliSimulationDTO(
            database_id=self.id,
            name=self.name,
            config=config_dto,
            last_updated=self.last_updated,
            job_name=self.job_name,
            job_id=self.job_id,
            metadata=metadata,
        )


async def create_db(async_engine: AsyncEngine) -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
