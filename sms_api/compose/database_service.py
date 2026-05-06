"""Database services for the compose subsystem (simulator, HPC, package registries)."""

import datetime
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pbest.utils.input_types import ContainerizationFileRepr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import InstrumentedAttribute
from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.compose.models import (
    BiGraphComputeType,
    BiGraphProcess,
    BiGraphStep,
    ComposeHpcRun,
    ComposeJobType,
    ComposeSimulation,
    ComposeSimulationRequest,
    ComposeSimulationResults,
    ComposeSimulatorVersion,
    ComposeSubmittedSimulation,
    ComposeWorkerEvent,
    PackageOutline,
    RegisteredPackage,
    get_singularity_hash,
)
from sms_api.compose.tables_orm import (
    BiGraphComputeTypeDB,
    ComposeJobStatusDB,
    ComposeJobTypeDB,
    ORMComposeBiGraphCompute,
    ORMComposeHpcRun,
    ORMComposePackage,
    ORMComposeSimulation,
    ORMComposeSimulator,
    ORMComposeSimulatorToPackage,
    ORMComposeWorkerEvent,
    PackageTypeDB,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HPC path helper (used by simulator DB to build result paths)
# ---------------------------------------------------------------------------


def _get_experiment_dir(experiment_id: str) -> str:
    from sms_api.config import get_settings

    settings = get_settings()
    return f"{settings.compose_sim_base_path}/experiment-{experiment_id}"


# ---------------------------------------------------------------------------
# Simulator database service
# ---------------------------------------------------------------------------


class SimulatorDatabaseService(ABC):
    @abstractmethod
    async def insert_simulator(
        self, singularity_def_rep: ContainerizationFileRepr, packages_used: list[RegisteredPackage] | None = None
    ) -> ComposeSimulatorVersion:
        pass

    @abstractmethod
    async def get_simulator(self, simulator_id: int) -> ComposeSimulatorVersion | None:
        pass

    @abstractmethod
    async def get_simulator_by_def_hash(self, singularity_def_hash: str) -> ComposeSimulatorVersion | None:
        pass

    @abstractmethod
    async def list_simulators(self) -> list[ComposeSimulatorVersion]:
        pass

    @abstractmethod
    async def insert_simulation(
        self, sim_request: ComposeSimulationRequest, experiment_id: str, simulator_version: ComposeSimulatorVersion
    ) -> ComposeSimulation:
        pass

    @abstractmethod
    async def get_simulations_experiment_id(self, simulation_id: int) -> str:
        pass

    @abstractmethod
    async def list_simulations(self) -> list[ComposeSubmittedSimulation]:
        pass


class SimulatorORMExecutor(SimulatorDatabaseService):
    async_session_maker: async_sessionmaker[AsyncSession]

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.async_session_maker = session_maker

    @override
    async def insert_simulator(
        self, singularity_def_rep: ContainerizationFileRepr, packages_used: list[RegisteredPackage] | None = None
    ) -> ComposeSimulatorVersion:
        async with self.async_session_maker() as session, session.begin():
            singularity_hash = get_singularity_hash(singularity_def_rep)
            existing = (
                (
                    await session.execute(
                        select(ORMComposeSimulator).where(ORMComposeSimulator.singularity_def_hash == singularity_hash)
                    )
                )
                .scalars()
                .first()
            )
            if existing is not None:
                raise RuntimeError(f"Simulator with hash={singularity_hash} already exists")

            orm = ORMComposeSimulator(
                singularity_def=singularity_def_rep.representation,
                singularity_def_hash=singularity_hash,
            )
            session.add(orm)
            await session.flush()

            if packages_used is not None:
                for pkg in packages_used:
                    session.add(ORMComposeSimulatorToPackage(simulator_id=orm.id, package_id=pkg.database_id))

            return orm.to_simulator_version()

    @override
    async def get_simulator(self, simulator_id: int) -> ComposeSimulatorVersion | None:
        async with self.async_session_maker() as session:
            orm = (
                (await session.execute(select(ORMComposeSimulator).where(ORMComposeSimulator.id == simulator_id)))
                .scalars()
                .first()
            )
            return orm.to_simulator_version() if orm else None

    @override
    async def get_simulator_by_def_hash(self, singularity_def_hash: str) -> ComposeSimulatorVersion | None:
        async with self.async_session_maker() as session:
            orm = (
                (
                    await session.execute(
                        select(ORMComposeSimulator).where(
                            ORMComposeSimulator.singularity_def_hash == singularity_def_hash
                        )
                    )
                )
                .scalars()
                .first()
            )
            return orm.to_simulator_version() if orm else None

    @override
    async def list_simulators(self) -> list[ComposeSimulatorVersion]:
        async with self.async_session_maker() as session:
            result = await session.execute(select(ORMComposeSimulator))
            return [orm.to_simulator_version() for orm in result.scalars().all()]

    @override
    async def insert_simulation(
        self, sim_request: ComposeSimulationRequest, experiment_id: str, simulator_version: ComposeSimulatorVersion
    ) -> ComposeSimulation:
        async with self.async_session_maker() as session, session.begin():
            orm = ORMComposeSimulation(experiment_id=experiment_id, simulator_id=simulator_version.database_id)
            session.add(orm)
            await session.flush()
            return ComposeSimulation(database_id=orm.id, sim_request=sim_request, simulator_version=simulator_version)

    @override
    async def get_simulations_experiment_id(self, simulation_id: int) -> str:
        async with self.async_session_maker() as session:
            orm = (
                (await session.execute(select(ORMComposeSimulation).where(ORMComposeSimulation.id == simulation_id)))
                .scalars()
                .first()
            )
            if orm is None:
                raise LookupError(f"Compose simulation {simulation_id} not found")
            return orm.experiment_id

    @override
    async def list_simulations(self) -> list[ComposeSubmittedSimulation]:
        async with self.async_session_maker() as session:
            result = await session.execute(
                select(ORMComposeSimulation, ORMComposeSimulator).join(
                    ORMComposeSimulator, onclause=ORMComposeSimulation.simulator_id == ORMComposeSimulator.id
                )
            )
            sims: list[ComposeSubmittedSimulation] = []
            for row in result.fetchall():
                orm_sim, orm_simulator = row.t
                hpc_run = await _get_hpc_run_by_correlation(session, orm_sim.experiment_id)
                sims.append(
                    ComposeSubmittedSimulation(
                        database_id=orm_sim.id,
                        sim_content=ComposeSimulationResults(
                            path_on_server=Path(_get_experiment_dir(orm_sim.experiment_id))
                        ),
                        simulator_version=orm_simulator.to_simulator_version(),
                        hpc_run=hpc_run,
                    )
                )
            return sims


async def _get_hpc_run_by_correlation(session: AsyncSession, correlation_id: str) -> ComposeHpcRun | None:
    orm = (
        (
            await session.execute(
                select(ORMComposeHpcRun).where(ORMComposeHpcRun.correlation_id == correlation_id).limit(1)
            )
        )
        .scalars()
        .first()
    )
    return orm.to_hpc_run() if orm else None


# ---------------------------------------------------------------------------
# HPC database service
# ---------------------------------------------------------------------------


class HPCDatabaseService(ABC):
    @abstractmethod
    async def insert_hpcrun(
        self, slurmjobid: int, job_type: ComposeJobType, ref_id: int, correlation_id: str
    ) -> ComposeHpcRun:
        pass

    @abstractmethod
    async def get_hpcrun_by_ref(self, ref_id: int, job_type: ComposeJobType) -> ComposeHpcRun | None:
        pass

    @abstractmethod
    async def get_hpcruns_by_refs(self, ref_ids: list[int], job_type: ComposeJobType) -> list[ComposeHpcRun]:
        pass

    @abstractmethod
    async def get_hpcrun_by_slurmjobid(self, slurmjobid: int) -> ComposeHpcRun | None:
        pass

    @abstractmethod
    async def get_hpcrun_id_by_correlation_id(self, correlation_id: str) -> int | None:
        pass

    @abstractmethod
    async def get_hpcrun_id_by_simulator_id(self, simulator_id: int) -> int | None:
        pass

    @abstractmethod
    async def list_running_hpcruns(self) -> list[ComposeHpcRun]:
        pass

    @abstractmethod
    async def update_hpcrun_status(self, hpcrun_id: int, new_slurm_job: SlurmJob) -> None:
        pass

    @abstractmethod
    async def insert_worker_event(self, worker_event: ComposeWorkerEvent, hpcrun_id: int) -> ComposeWorkerEvent:
        pass


class HPCORMExecutor(HPCDatabaseService):
    async_session_maker: async_sessionmaker[AsyncSession]

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.async_session_maker = session_maker

    def _get_job_type_ref(self, job_type: ComposeJobType) -> InstrumentedAttribute[int | None]:
        match job_type:
            case ComposeJobType.SIMULATION:
                return ORMComposeHpcRun.simulation_id
            case ComposeJobType.BUILD_CONTAINER:
                return ORMComposeHpcRun.simulator_id

    @override
    async def insert_hpcrun(
        self, slurmjobid: int, job_type: ComposeJobType, ref_id: int, correlation_id: str
    ) -> ComposeHpcRun:
        async with self.async_session_maker() as session, session.begin():
            simulation_key = ref_id if job_type == ComposeJobType.SIMULATION else None
            simulator_key = ref_id if job_type == ComposeJobType.BUILD_CONTAINER else None
            orm = ORMComposeHpcRun(
                slurmjobid=slurmjobid,
                job_type=ComposeJobTypeDB.from_job_type(job_type),
                status=ComposeJobStatusDB.RUNNING,
                simulation_id=simulation_key,
                simulator_id=simulator_key,
                start_time=datetime.datetime.now(),
                correlation_id=correlation_id,
            )
            session.add(orm)
            await session.flush()
            return orm.to_hpc_run()

    @override
    async def get_hpcrun_by_ref(self, ref_id: int, job_type: ComposeJobType) -> ComposeHpcRun | None:
        async with self.async_session_maker() as session:
            ref_col = self._get_job_type_ref(job_type)
            orm = (await session.execute(select(ORMComposeHpcRun).where(ref_col == ref_id).limit(1))).scalars().first()
            return orm.to_hpc_run() if orm else None

    @override
    async def get_hpcruns_by_refs(self, ref_ids: list[int], job_type: ComposeJobType) -> list[ComposeHpcRun]:
        async with self.async_session_maker() as session:
            ref_col = self._get_job_type_ref(job_type)
            result = await session.execute(select(ORMComposeHpcRun).where(ref_col.in_(ref_ids)))
            return [orm.to_hpc_run() for orm in result.scalars().all()]

    @override
    async def get_hpcrun_by_slurmjobid(self, slurmjobid: int) -> ComposeHpcRun | None:
        async with self.async_session_maker() as session:
            orm = (
                (
                    await session.execute(
                        select(ORMComposeHpcRun).where(ORMComposeHpcRun.slurmjobid == slurmjobid).limit(1)
                    )
                )
                .scalars()
                .first()
            )
            return orm.to_hpc_run() if orm else None

    @override
    async def get_hpcrun_id_by_correlation_id(self, correlation_id: str) -> int | None:
        async with self.async_session_maker() as session:
            return (
                await session.execute(
                    select(ORMComposeHpcRun.id).where(ORMComposeHpcRun.correlation_id == correlation_id).limit(1)
                )
            ).scalar_one_or_none()

    @override
    async def get_hpcrun_id_by_simulator_id(self, simulator_id: int) -> int | None:
        async with self.async_session_maker() as session:
            return (
                await session.execute(
                    select(ORMComposeHpcRun.id).where(ORMComposeHpcRun.simulator_id == simulator_id).limit(1)
                )
            ).scalar_one_or_none()

    @override
    async def list_running_hpcruns(self) -> list[ComposeHpcRun]:
        async with self.async_session_maker() as session:
            result = await session.execute(
                select(ORMComposeHpcRun).where(ORMComposeHpcRun.status == ComposeJobStatusDB.RUNNING)
            )
            return [orm.to_hpc_run() for orm in result.scalars().all()]

    @override
    async def update_hpcrun_status(self, hpcrun_id: int, new_slurm_job: SlurmJob) -> None:
        async with self.async_session_maker() as session, session.begin():
            orm = (
                (await session.execute(select(ORMComposeHpcRun).where(ORMComposeHpcRun.id == hpcrun_id)))
                .scalars()
                .first()
            )
            if orm is None:
                raise RuntimeError(f"ComposeHpcRun {hpcrun_id} not found")
            orm.status = ComposeJobStatusDB(new_slurm_job.job_state.lower())
            if new_slurm_job.start_time is not None:
                orm.start_time = datetime.datetime.fromisoformat(new_slurm_job.start_time)
            if new_slurm_job.end_time is not None:
                orm.end_time = datetime.datetime.fromisoformat(new_slurm_job.end_time)
            await session.flush()

    @override
    async def insert_worker_event(self, worker_event: ComposeWorkerEvent, hpcrun_id: int) -> ComposeWorkerEvent:
        async with self.async_session_maker() as session, session.begin():
            orm = ORMComposeWorkerEvent.from_worker_event(worker_event, hpcrun_id=hpcrun_id)
            session.add(orm)
            await session.flush()
            return orm.to_worker_event()


# ---------------------------------------------------------------------------
# Package database service
# ---------------------------------------------------------------------------


class PackageDatabaseService(ABC):
    @abstractmethod
    async def insert_package(self, package_outline: PackageOutline) -> RegisteredPackage:
        pass

    @abstractmethod
    async def list_all_computes(self, compute_type: BiGraphComputeType | None = None) -> Any:
        pass


class PackageORMExecutor(PackageDatabaseService):
    async_session_maker: async_sessionmaker[AsyncSession]

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.async_session_maker = session_maker

    @override
    async def insert_package(self, package: PackageOutline) -> RegisteredPackage:
        async with self.async_session_maker() as session, session.begin():
            orm_pkg = ORMComposePackage(
                package_type=PackageTypeDB.from_package_type(package.package_type),
                name=package.name,
            )
            session.add(orm_pkg)
            await session.flush()

            processes: list[BiGraphProcess] = []
            steps: list[BiGraphStep] = []
            for compute in package.compute:
                orm_compute = ORMComposeBiGraphCompute(
                    module=compute.module,
                    name=compute.name,
                    compute_type=BiGraphComputeTypeDB.from_compute_type(compute.compute_type),
                    inputs=compute.inputs,
                    outputs=compute.outputs,
                    package_ref=orm_pkg.id,
                )
                session.add(orm_compute)
                await session.flush()
                if orm_compute.compute_type == BiGraphComputeTypeDB.PROCESS:
                    processes.append(orm_compute.to_bigraph_process())
                else:
                    steps.append(orm_compute.to_bigraph_step())

            return orm_pkg.to_bigraph_package(processes, steps)

    @override
    async def list_all_computes(self, compute_type: BiGraphComputeType | None = None) -> Any:
        async with self.async_session_maker() as session:
            stmt = select(ORMComposeBiGraphCompute)
            if compute_type is not None:
                stmt = stmt.where(
                    ORMComposeBiGraphCompute.compute_type == BiGraphComputeTypeDB.from_compute_type(compute_type)
                )
            result = await session.execute(stmt)
            orms = result.scalars().all()
            match compute_type:
                case BiGraphComputeType.PROCESS:
                    return [o.to_bigraph_process() for o in orms]
                case BiGraphComputeType.STEP:
                    return [o.to_bigraph_step() for o in orms]
                case _:
                    return [o.to_bigraph_compute() for o in orms]


# ---------------------------------------------------------------------------
# Facade
# ---------------------------------------------------------------------------


class ComposeDatabaseService:
    """Aggregated database service for the compose subsystem."""

    simulator_db: SimulatorDatabaseService
    hpc_db: HPCDatabaseService
    package_db: PackageDatabaseService

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.simulator_db = SimulatorORMExecutor(session_maker)
        self.hpc_db = HPCORMExecutor(session_maker)
        self.package_db = PackageORMExecutor(session_maker)

    def get_simulator_db(self) -> SimulatorDatabaseService:
        return self.simulator_db

    def get_hpc_db(self) -> HPCDatabaseService:
        return self.hpc_db

    def get_package_db(self) -> PackageDatabaseService:
        return self.package_db
