import datetime
import enum
from typing import Optional

from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sms_api.simulation.models import JobStatus


class JobStatusDB(enum.Enum):
    WAITING = "waiting"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

    def to_job_status(self) -> JobStatus:
        return JobStatus(self.value)


class JobType(enum.Enum):
    SIMULATION = "simulation"
    PARCA = "parca"


class Base(AsyncAttrs, DeclarativeBase):
    pass


class ORMSimulator(Base):
    __tablename__ = "simulator"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    git_repo_url: Mapped[str] = mapped_column(nullable=False)
    git_branch: Mapped[str] = mapped_column(nullable=False)
    git_commit_hash: Mapped[str] = mapped_column(nullable=False)  # first 7 characters of the commit hash
    hpcrun_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hpcrun.id"), nullable=True, index=True)


class ORMHpcRun(Base):
    __tablename__ = "hpcrun"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    job_type: Mapped[JobType] = mapped_column(nullable=False)
    slurmjobid: Mapped[Optional[int]] = mapped_column(nullable=True)
    start_time: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    end_time: Mapped[Optional[datetime.datetime]] = mapped_column(nullable=True)
    status: Mapped[JobStatusDB] = mapped_column(nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(nullable=True)


class ORMParcaDataset(Base):
    __tablename__ = "parca_dataset"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    simulator_id: Mapped[int] = mapped_column(ForeignKey("simulator.id"), nullable=False, index=True)
    parca_config: Mapped[dict[str, int | float | str]] = mapped_column(JSONB, nullable=False)
    parca_config_hash: Mapped[str] = mapped_column(nullable=False)
    hpcrun_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hpcrun.id"), nullable=True, index=True)
    remote_archive_path: Mapped[Optional[str]] = mapped_column(nullable=True)


class ORMSimulation(Base):
    __tablename__ = "simulation"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    simulator_id: Mapped[int] = mapped_column(ForeignKey("simulator.id"), nullable=False, index=True)
    parca_dataset_id: Mapped[int] = mapped_column(ForeignKey("parca_dataset.id"), nullable=False, index=True)
    variant_config: Mapped[dict[str, dict[str, int | float | str]]] = mapped_column(JSONB, nullable=False)
    variant_config_hash: Mapped[str] = mapped_column(nullable=False)
    hpcrun_id: Mapped[Optional[int]] = mapped_column(ForeignKey("hpcrun.id"), nullable=True, index=True)


async def create_db(async_engine: AsyncEngine) -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
