import datetime
import enum
from typing import Optional

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sms_api.simulation.models import HpcRun, JobStatus, JobType, WorkerEvent


class JobStatusDB(enum.Enum):
    WAITING = "waiting"
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


class ORMHpcRun(Base):
    __tablename__ = "hpcrun"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    job_type: Mapped[JobTypeDB] = mapped_column(nullable=False)
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
            job_type=self.job_type.to_job_type(),
            ref_id=ref_id,
            status=self.status.to_job_status(),
            error_message=self.error_message,
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

    sequence_number: Mapped[int] = mapped_column(nullable=False, index=True)
    sim_data: Mapped[list[tuple[str, str, float]]] = mapped_column(JSONB, nullable=False)
    global_time: Mapped[Optional[float]] = mapped_column(nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(nullable=True)
    hpcrun_id: Mapped[int] = mapped_column(ForeignKey("hpcrun.id"), nullable=False, index=True)

    @classmethod
    def from_worker_event(cls, worker_event: "WorkerEvent") -> "ORMWorkerEvent":
        return cls(
            sequence_number=worker_event.sequence_number,
            sim_data=worker_event.sim_data,
            global_time=worker_event.global_time,
            error_message=worker_event.error_message,
            hpcrun_id=worker_event.hpcrun_id,
        )

    def to_worker_event(self) -> WorkerEvent:
        return WorkerEvent(
            database_id=self.id,
            created_at=str(self.created_at),
            sequence_number=self.sequence_number,
            sim_data=self.sim_data,
            global_time=self.global_time,
            error_message=self.error_message,
            hpcrun_id=self.hpcrun_id,
        )


async def create_db(async_engine: AsyncEngine) -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
