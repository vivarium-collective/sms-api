import datetime
import logging
from abc import ABC, abstractmethod

from sqlalchemy import Result, and_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import InstrumentedAttribute
from typing_extensions import override

from sms_api.analysis.models import AnalysisConfig, ExperimentAnalysisDTO
from sms_api.common.hpc.models import SlurmJob
from sms_api.config import get_settings
from sms_api.simulation.models import (
    HpcRun,
    JobType,
    ParcaDataset,
    ParcaDatasetRequest,
    ParcaOptions,
    Simulation,
    SimulationConfig,
    SimulationRequest,
    SimulatorVersion,
    WorkerEvent,
)
from sms_api.simulation.tables_orm import (
    JobStatusDB,
    JobTypeDB,
    ORMAnalysis,
    ORMHpcRun,
    ORMParcaDataset,
    ORMSimulation,
    ORMSimulator,
    ORMWorkerEvent,
)

logger = logging.getLogger(__name__)


class DatabaseService(ABC):
    @abstractmethod
    async def insert_analysis(
        self, name: str, config: AnalysisConfig, last_updated: str, job_name: str, job_id: int
    ) -> ExperimentAnalysisDTO:
        """Used by the /ecoli router"""
        pass

    @abstractmethod
    async def get_analysis(self, database_id: int) -> ExperimentAnalysisDTO:
        """Used by the /ecoli router"""
        pass

    @abstractmethod
    async def list_analyses(self) -> list[ExperimentAnalysisDTO]:
        """Used by the /ecoli router"""
        pass

    ####################################

    @abstractmethod
    async def insert_worker_event(self, worker_event: WorkerEvent, hpcrun_id: int) -> WorkerEvent:
        pass

    @abstractmethod
    async def list_worker_events(self, hpcrun_id: int, prev_sequence_number: int | None = None) -> list[WorkerEvent]:
        pass

    @abstractmethod
    async def insert_simulator(self, git_commit_hash: str, git_repo_url: str, git_branch: str) -> SimulatorVersion:
        pass

    @abstractmethod
    async def get_simulator(self, simulator_id: int) -> SimulatorVersion | None:
        pass

    @abstractmethod
    async def get_simulator_by_commit(self, commit_hash: str) -> SimulatorVersion | None:
        pass

    @abstractmethod
    async def delete_simulator(self, simulator_id: int) -> None:
        pass

    @abstractmethod
    async def list_simulators(self) -> list[SimulatorVersion]:
        pass

    @abstractmethod
    async def insert_hpcrun(self, slurmjobid: int, job_type: JobType, ref_id: int, correlation_id: str) -> HpcRun:
        """
        :param slurmjobid: (`int`) slurm job id for the associated `job_type`.
        :param job_type: (`JobType`) job type to be run. Choose one of the following:
            `JobType.SIMULATION`(/vecoli/run), `JobType.PARCA`(/vecoli/parca), `JobType.BUILD_IMAGE`(/simulator/new)
        :param ref_id: primary key of the object this HPC run is associated with (sim, parca, etc.).
        """
        pass

    @abstractmethod
    async def get_hpcrun_by_ref(self, ref_id: int, job_type: JobType) -> HpcRun | None:
        pass

    @abstractmethod
    async def get_hpcrun_by_slurmjobid(self, slurmjobid: int) -> HpcRun | None:
        pass

    @abstractmethod
    async def get_hpcrun(self, hpcrun_id: int) -> HpcRun | None:
        pass

    @abstractmethod
    async def get_hpcrun_id_by_correlation_id(self, correlation_id: str) -> int | None:
        pass

    @abstractmethod
    async def delete_hpcrun(self, hpcrun_id: int) -> None:
        pass

    @abstractmethod
    async def insert_parca_dataset(self, parca_dataset_request: ParcaDatasetRequest) -> ParcaDataset:
        pass

    @abstractmethod
    async def get_parca_dataset(self, parca_dataset_id: int) -> ParcaDataset | None:
        pass

    @abstractmethod
    async def delete_parca_dataset(self, parca_dataset_id: int) -> None:
        pass

    @abstractmethod
    async def list_parca_datasets(self) -> list[ParcaDataset]:
        pass

    @abstractmethod
    async def insert_simulation(self, sim_request: SimulationRequest) -> Simulation:
        pass

    @abstractmethod
    async def get_simulation(self, simulation_id: int) -> Simulation | None:
        pass

    @abstractmethod
    async def delete_simulation(self, simulation_id: int) -> None:
        pass

    @abstractmethod
    async def list_simulations(self) -> list[Simulation]:
        pass

    @abstractmethod
    async def list_running_hpcruns(self) -> list[HpcRun]:
        """Return all HpcRun jobs with status RUNNING."""
        pass

    @abstractmethod
    async def update_hpcrun_status(self, hpcrun_id: int, new_slurm_job: SlurmJob) -> None:
        """Update the status of a given HpcRun job."""
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class DatabaseServiceSQL(DatabaseService):
    async_sessionmaker: async_sessionmaker[AsyncSession]

    def __init__(self, async_engine: AsyncEngine):
        self.async_sessionmaker = async_sessionmaker(async_engine, expire_on_commit=True)

    async def _get_orm_simulator(self, session: AsyncSession, simulator_id: int) -> ORMSimulator | None:
        stmt1 = select(ORMSimulator).where(ORMSimulator.id == simulator_id).limit(1)
        result1: Result[tuple[ORMSimulator]] = await session.execute(stmt1)
        orm_simulator: ORMSimulator | None = result1.scalars().one_or_none()
        return orm_simulator

    async def _get_orm_simulation(self, session: AsyncSession, simulation_id: int) -> ORMSimulation | None:
        stmt1 = select(ORMSimulation).where(ORMSimulation.id == simulation_id).limit(1)
        result1: Result[tuple[ORMSimulation]] = await session.execute(stmt1)
        orm_simulation: ORMSimulation | None = result1.scalars().one_or_none()
        return orm_simulation

    async def _get_orm_parca_dataset(self, session: AsyncSession, parca_dataset_id: int) -> ORMParcaDataset | None:
        stmt1 = select(ORMParcaDataset).where(ORMParcaDataset.id == parca_dataset_id).limit(1)
        result1: Result[tuple[ORMParcaDataset]] = await session.execute(stmt1)
        orm_parca_dataset: ORMParcaDataset | None = result1.scalars().one_or_none()
        return orm_parca_dataset

    async def _get_orm_hpcrun(self, session: AsyncSession, hpcrun_id: int) -> ORMHpcRun | None:
        stmt1 = select(ORMHpcRun).where(ORMHpcRun.id == hpcrun_id).limit(1)
        result1: Result[tuple[ORMHpcRun]] = await session.execute(stmt1)
        orm_hpc_job: ORMHpcRun | None = result1.scalars().one_or_none()
        return orm_hpc_job

    async def _get_orm_hpcrun_by_slurmjobid(self, session: AsyncSession, slurmjobid: int) -> ORMHpcRun | None:
        stmt1 = select(ORMHpcRun).where(ORMHpcRun.slurmjobid == slurmjobid).limit(1)
        result1: Result[tuple[ORMHpcRun]] = await session.execute(stmt1)
        orm_hpc_job: ORMHpcRun | None = result1.scalars().one_or_none()
        return orm_hpc_job

    def _get_job_type_ref(self, job_type: JobType) -> InstrumentedAttribute[int | None] | None:
        match job_type:
            case JobType.BUILD_IMAGE:
                return ORMHpcRun.jobref_simulator_id
            case JobType.PARCA:
                return ORMHpcRun.jobref_parca_dataset_id
            case JobType.SIMULATION:
                return ORMHpcRun.jobref_simulation_id
        return None

    async def _get_orm_hpcrun_by_ref(self, session: AsyncSession, ref_id: int, job_type: JobType) -> ORMHpcRun | None:
        reference = self._get_job_type_ref(job_type)
        stmt1 = select(ORMHpcRun).where(reference == ref_id).limit(1)  # type: ignore[arg-type]
        result1: Result[tuple[ORMHpcRun]] = await session.execute(stmt1)
        orm_hpc_job: ORMHpcRun | None = result1.scalars().one_or_none()

        return orm_hpc_job

    async def _get_orm_analysis(self, session: AsyncSession, database_id: int) -> ORMAnalysis | None:
        """Used by the /ecoli router"""
        stmt1 = select(ORMAnalysis).where(ORMAnalysis.id == database_id).limit(1)
        result1: Result[tuple[ORMAnalysis]] = await session.execute(stmt1)
        orm_experiment: ORMAnalysis | None = result1.scalars().one_or_none()
        return orm_experiment

    @override
    async def insert_analysis(
        self, name: str, config: AnalysisConfig, last_updated: str, job_name: str, job_id: int
    ) -> ExperimentAnalysisDTO:
        """Used by the /ecoli router"""
        async with self.async_sessionmaker() as session, session.begin():
            config.emitter_arg["out_dir"] = str(get_settings().simulation_outdir)
            orm_analysis = ORMAnalysis(
                name=name, config=config.model_dump(), last_updated=last_updated, job_name=job_name, job_id=job_id
            )
            session.add(orm_analysis)
            await session.flush()
            return orm_analysis.to_dto()

    @override
    async def get_analysis(self, database_id: int) -> ExperimentAnalysisDTO:
        """Used by the /ecoli router"""
        async with self.async_sessionmaker() as session, session.begin():
            orm_analysis = await self._get_orm_analysis(session, database_id=database_id)
            if orm_analysis is None:
                raise RuntimeError(f"Experiment {database_id} not found")
            return orm_analysis.to_dto()

    @override
    async def list_analyses(self) -> list[ExperimentAnalysisDTO]:
        """Used by the /ecoli router"""
        async with self.async_sessionmaker() as session:
            stmt = select(ORMAnalysis)
            result: Result[tuple[ORMAnalysis]] = await session.execute(stmt)
            orm_analyses = result.scalars().all()

            versions: list[ExperimentAnalysisDTO] = []
            for experiment in orm_analyses:
                versions.append(experiment.to_dto())
            return versions

    ##################################

    @override
    async def insert_simulator(self, git_commit_hash: str, git_repo_url: str, git_branch: str) -> SimulatorVersion:
        async with self.async_sessionmaker() as session, session.begin():
            stmt1 = (
                select(ORMSimulator)
                .where(
                    and_(
                        ORMSimulator.git_commit_hash == git_commit_hash,
                        ORMSimulator.git_repo_url == git_repo_url,
                        ORMSimulator.git_branch == git_branch,
                    )
                )
                .limit(1)
            )
            result1: Result[tuple[ORMSimulator]] = await session.execute(stmt1)
            existing_orm_simulator: ORMSimulator | None = result1.scalars().one_or_none()
            if existing_orm_simulator is not None:
                # If the simulator already exists
                logger.error(
                    f"Simulator with git_commit_hash={git_commit_hash}, git_repo_url={git_repo_url}, "
                    f"git_branch={git_branch} already exists in the database"
                )
                raise RuntimeError(f"Simulator with git_commit_hash={git_commit_hash} already exists in the database")

            # did not find the simulator, so insert it
            new_orm_simulator = ORMSimulator(
                git_commit_hash=git_commit_hash,
                git_repo_url=git_repo_url,
                git_branch=git_branch,
            )
            session.add(new_orm_simulator)
            await session.flush()
            # Ensure the ORM object is inserted and has an ID
            return new_orm_simulator.to_simulator_version()

    @override
    async def get_simulator(self, simulator_id: int) -> SimulatorVersion | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_simulator = await self._get_orm_simulator(session, simulator_id=simulator_id)
            if orm_simulator is None:
                return None
            return orm_simulator.to_simulator_version()

    @override
    async def get_simulator_by_commit(self, commit_hash: str) -> SimulatorVersion | None:
        async with self.async_sessionmaker() as session, session.begin():
            stmt1 = select(ORMSimulator).where(ORMSimulator.git_commit_hash == commit_hash).limit(1)
            result1: Result[tuple[ORMSimulator]] = await session.execute(stmt1)
            orm_simulator: ORMSimulator | None = result1.scalars().one_or_none()
            if orm_simulator is None:
                return None
            return orm_simulator.to_simulator_version()

    @override
    async def delete_simulator(self, simulator_id: int) -> None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_simulator: ORMSimulator | None = await self._get_orm_simulator(session, simulator_id=simulator_id)
            if orm_simulator is None:
                raise Exception(f"Simulator with id {simulator_id} not found in the database")
            await session.delete(orm_simulator)

    @override
    async def list_simulators(self) -> list[SimulatorVersion]:
        async with self.async_sessionmaker() as session:
            stmt = select(ORMSimulator)
            result: Result[tuple[ORMSimulator]] = await session.execute(stmt)
            orm_simulators = result.scalars().all()

            simulator_versions: list[SimulatorVersion] = []
            for orm_simulator in orm_simulators:
                simulator_versions.append(orm_simulator.to_simulator_version())
            return simulator_versions

    @override
    async def insert_hpcrun(self, slurmjobid: int, job_type: JobType, ref_id: int, correlation_id: str) -> HpcRun:
        jobref_simulation_id = ref_id if job_type == JobType.SIMULATION else None
        # jobref_parca_dataset_id = None if job_type == JobType.PARCA else None
        # jobref_simulator_id = None if job_type == JobType.BUILD_IMAGE else None
        jobref_parca_dataset_id = ref_id if job_type == JobType.PARCA else None
        jobref_simulator_id = ref_id if job_type == JobType.BUILD_IMAGE else None
        async with self.async_sessionmaker() as session, session.begin():
            orm_hpc_run = ORMHpcRun(
                slurmjobid=slurmjobid,
                job_type=JobTypeDB.from_job_type(job_type),
                status=JobStatusDB.RUNNING,
                jobref_simulator_id=jobref_simulator_id,
                jobref_simulation_id=jobref_simulation_id,
                jobref_parca_dataset_id=jobref_parca_dataset_id,
                start_time=datetime.datetime.now(),
                correlation_id=correlation_id,
            )
            session.add(orm_hpc_run)
            await session.flush()
            return orm_hpc_run.to_hpc_run()

    @override
    async def get_hpcrun_by_slurmjobid(self, slurmjobid: int) -> HpcRun | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_hpc_job: ORMHpcRun | None = await self._get_orm_hpcrun_by_slurmjobid(session, slurmjobid=slurmjobid)
            if orm_hpc_job is None:
                return None
            return orm_hpc_job.to_hpc_run()

    @override
    async def get_hpcrun_by_ref(self, ref_id: int, job_type: JobType) -> HpcRun | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_hpc_job: ORMHpcRun | None = await self._get_orm_hpcrun_by_ref(session, ref_id=ref_id, job_type=job_type)
            if orm_hpc_job is None:
                return None
            return orm_hpc_job.to_hpc_run()

    @override
    async def get_hpcrun(self, hpcrun_id: int) -> HpcRun | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_hpc_job: ORMHpcRun | None = await self._get_orm_hpcrun(session, hpcrun_id=hpcrun_id)
            if orm_hpc_job is None:
                return None
            return orm_hpc_job.to_hpc_run()

    @override
    async def delete_hpcrun(self, hpcrun_id: int) -> None:
        async with self.async_sessionmaker() as session, session.begin():
            hpcrun: ORMHpcRun | None = await self._get_orm_hpcrun(session, hpcrun_id=hpcrun_id)
            if hpcrun is None:
                raise Exception(f"HpcRun with id {hpcrun_id} not found in the database")
            await session.delete(hpcrun)

    @override
    async def insert_parca_dataset(self, parca_dataset_request: ParcaDatasetRequest) -> ParcaDataset:
        async with self.async_sessionmaker() as session, session.begin():
            simulator_id = parca_dataset_request.simulator_version.database_id
            stmt1 = (
                select(ORMParcaDataset)
                .where(
                    and_(
                        ORMParcaDataset.simulator_id == simulator_id,
                        ORMParcaDataset.parca_config_hash == parca_dataset_request.config_hash,
                    )
                )
                .limit(1)
            )
            result1: Result[tuple[ORMParcaDataset]] = await session.execute(stmt1)
            existing_orm_parca_dataset: ORMParcaDataset | None = result1.scalars().one_or_none()
            if existing_orm_parca_dataset is not None:
                logger.info("Parca Dataset with the same configuration already exists in the database")
                return await self.get_parca_dataset(existing_orm_parca_dataset.id)  # type: ignore[return-value]

            # did not find the parca dataset, so insert it
            orm_simulator: ORMSimulator | None = await self._get_orm_simulator(session, simulator_id=simulator_id)
            if orm_simulator is None:
                raise Exception(f"Simulator with id {simulator_id} not found in the database")
            orm_parca_dataset = ORMParcaDataset(
                simulator_id=orm_simulator.id,
                parca_config=parca_dataset_request.parca_config.model_dump(),
                parca_config_hash=parca_dataset_request.config_hash,
            )
            session.add(orm_parca_dataset)
            await session.flush()  # Ensure the ORM object is inserted and has an ID
            # Ensure the ORM object is inserted and has an ID
            orm_parca_dataset_id = orm_parca_dataset.id
            # Prepare the ParcaDataset object to return
            simulator_version = SimulatorVersion(
                database_id=orm_simulator.id,
                git_commit_hash=orm_simulator.git_commit_hash,
                git_repo_url=orm_simulator.git_repo_url,
                git_branch=orm_simulator.git_branch,
            )
            parca_dataset_request = ParcaDatasetRequest(
                simulator_version=simulator_version,
                parca_config=ParcaOptions(**orm_parca_dataset.parca_config),  # type: ignore[arg-type]
            )
            parca_dataset = ParcaDataset(
                database_id=orm_parca_dataset_id,
                parca_dataset_request=parca_dataset_request,
                remote_archive_path=None,
            )
            return parca_dataset

    @override
    async def get_parca_dataset(self, parca_dataset_id: int) -> ParcaDataset | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_parca_dataset: ORMParcaDataset | None = await self._get_orm_parca_dataset(
                session, parca_dataset_id=parca_dataset_id
            )
            if orm_parca_dataset is None:
                return None

            simulator_version: SimulatorVersion | None = await self.get_simulator(orm_parca_dataset.simulator_id)
            if simulator_version is None:
                raise Exception(f"Simulator with id {orm_parca_dataset.simulator_id} not found in the database")

            return ParcaDataset(
                database_id=orm_parca_dataset.id,
                parca_dataset_request=ParcaDatasetRequest(
                    simulator_version=simulator_version,
                    parca_config=ParcaOptions(**orm_parca_dataset.parca_config),  # type: ignore[arg-type]
                ),
                remote_archive_path=orm_parca_dataset.remote_archive_path,
            )

    @override
    async def delete_parca_dataset(self, parca_dataset: int) -> None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_parca_dataset: ORMParcaDataset | None = await self._get_orm_parca_dataset(
                session, parca_dataset_id=parca_dataset
            )
            if orm_parca_dataset is None:
                raise Exception(f"Parca Dataset with id {parca_dataset} not found in the database")
            await session.delete(orm_parca_dataset)

    @override
    async def list_parca_datasets(self) -> list[ParcaDataset]:
        async with self.async_sessionmaker() as session:
            stmt = select(ORMParcaDataset)
            result: Result[tuple[ORMParcaDataset]] = await session.execute(stmt)
            orm_parca_datasets = result.scalars().all()

            parca_datasets: list[ParcaDataset] = []
            for orm_parca_dataset in orm_parca_datasets:
                simulator_version: SimulatorVersion | None = await self.get_simulator(orm_parca_dataset.simulator_id)
                if simulator_version is None:
                    raise Exception(f"Simulator with id {orm_parca_dataset.simulator_id} not found in the database")
                parca_datasets.append(
                    ParcaDataset(
                        database_id=orm_parca_dataset.id,
                        parca_dataset_request=ParcaDatasetRequest(
                            simulator_version=simulator_version,
                            parca_config=ParcaOptions(**orm_parca_dataset.parca_config),  # type: ignore[arg-type]
                        ),
                        remote_archive_path=orm_parca_dataset.remote_archive_path,
                    )
                )
            return parca_datasets

    @override
    async def insert_worker_event(self, worker_event: WorkerEvent, hpcrun_id: int) -> WorkerEvent:
        async with self.async_sessionmaker() as session, session.begin():
            orm_worker_event = ORMWorkerEvent.from_worker_event(worker_event, hpcrun_id=hpcrun_id)
            session.add(orm_worker_event)
            await session.flush()  # Ensure the ORM object is inserted and has an ID

            # prepare the Simulation object to return
            new_worker_event = orm_worker_event.to_worker_event()
            return new_worker_event

    @override
    async def list_worker_events(self, hpcrun_id: int, prev_sequence_number: int | None = None) -> list[WorkerEvent]:
        async with self.async_sessionmaker() as session, session.begin():
            stmt = (
                select(
                    ORMWorkerEvent.mass,
                    ORMWorkerEvent.sequence_number,
                    ORMWorkerEvent.id,
                    ORMWorkerEvent.time,
                    ORMWorkerEvent.hpcrun_id,
                )
                .where(
                    and_(
                        ORMWorkerEvent.hpcrun_id == hpcrun_id,
                        ORMWorkerEvent.sequence_number > (prev_sequence_number or -1),
                    )
                )
                .order_by(ORMWorkerEvent.sequence_number)
            )
            result: Result[tuple[dict[str, float], int, int, float, int]] = await session.execute(stmt)
            orm_worker_events = result.all()

            worker_events: list[WorkerEvent] = []
            for orm_worker_event in orm_worker_events:
                worker_events.append(ORMWorkerEvent.from_query_results(orm_worker_event.tuple()))
            return worker_events

    @override
    async def insert_simulation(self, sim_request: SimulationRequest) -> Simulation:
        async with self.async_sessionmaker() as session, session.begin():
            simulator_id = sim_request.simulator_id
            orm_simulator = None
            if simulator_id is not None:
                orm_simulator = await self._get_orm_simulator(session, simulator_id)
            if orm_simulator is None and sim_request.simulator is not None:
                simulators = await self.list_simulators()
                matching_sim: SimulatorVersion | None = next(
                    (
                        sim
                        for sim in simulators
                        if sim.git_branch == sim_request.simulator.git_branch
                        and sim.git_repo_url == sim_request.simulator.git_repo_url
                        and sim.git_commit_hash == sim_request.simulator.git_commit_hash
                    ),
                    None,
                )
                if matching_sim is not None:
                    orm_simulator = await self._get_orm_simulator(session, matching_sim.database_id)

            if orm_simulator is None:
                raise Exception(f"Simulator specified in request: {sim_request} not found in the database")
            simulator_id = orm_simulator.id

            parca_id = sim_request.parca_dataset_id
            if parca_id is None:
                raise Exception(
                    f"Parca Dataset with not found in the database with reference to simulator: {simulator_id}"
                )
            orm_parca_dataset: ORMParcaDataset | None = await self._get_orm_parca_dataset(
                session, parca_dataset_id=parca_id
            )
            if orm_parca_dataset is None:
                raise Exception(f"Parca Dataset with id {sim_request.parca_dataset_id} not found in the database")
            if orm_parca_dataset.simulator_id != orm_simulator.id:
                raise Exception(
                    f"Parca Dataset simulator mismatch, id={orm_simulator.id} and {sim_request.simulator_id}"
                )

            sim_config = sim_request.config
            orm_simulation = ORMSimulation(
                simulator_id=simulator_id,
                parca_dataset_id=orm_parca_dataset.id,
                config=sim_config.model_dump(),
            )
            session.add(orm_simulation)
            await session.flush()  # Ensure the ORM object is inserted and has an ID

            simulation = Simulation(
                database_id=orm_simulation.id,
                simulator_id=orm_simulator.id,
                parca_dataset_id=sim_request.parca_dataset_id,  # type: ignore[arg-type]
                config=sim_config,
            )
            return simulation

    @override
    async def get_simulation(self, simulation_id: int) -> Simulation | None:
        async with self.async_sessionmaker() as session:
            orm_simulation: ORMSimulation | None = await self._get_orm_simulation(session, simulation_id)
            if orm_simulation is None:
                return None

            simulation = Simulation(
                database_id=orm_simulation.id,
                simulator_id=orm_simulation.simulator_id,
                parca_dataset_id=orm_simulation.parca_dataset_id,
                config=SimulationConfig(**orm_simulation.config),  # type: ignore[arg-type]
            )
            return simulation

    @override
    async def delete_simulation(self, simulation_id: int) -> None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_simulation: ORMSimulation | None = await self._get_orm_simulation(session, simulation_id)
            if orm_simulation is None:
                raise Exception(f"Simulation with id {simulation_id} not found in the database")
            await session.delete(orm_simulation)

    @override
    async def list_simulations(self) -> list[Simulation]:
        async with self.async_sessionmaker() as session:
            stmt = select(ORMSimulation)
            result: Result[tuple[ORMSimulation]] = await session.execute(stmt)
            orm_simulations = result.scalars().all()

            simulations: list[Simulation] = []
            for orm_simulation in orm_simulations:
                simulation = Simulation(
                    database_id=orm_simulation.id,
                    simulator_id=orm_simulation.simulator_id,
                    parca_dataset_id=orm_simulation.parca_dataset_id,
                    config=SimulationConfig(**orm_simulation.config),  # type: ignore[arg-type]
                )
                simulations.append(simulation)

            return simulations

    @override
    async def list_running_hpcruns(self) -> list[HpcRun]:
        async with self.async_sessionmaker() as session:
            stmt = select(ORMHpcRun).where(ORMHpcRun.status == JobStatusDB.RUNNING)
            result: Result[tuple[ORMHpcRun]] = await session.execute(stmt)
            orm_hpcruns = result.scalars().all()
            return [orm_hpcrun.to_hpc_run() for orm_hpcrun in orm_hpcruns]

    @override
    async def update_hpcrun_status(self, hpcrun_id: int, new_slurm_job: SlurmJob) -> None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_hpcrun: ORMHpcRun | None = await self._get_orm_hpcrun(session, hpcrun_id=hpcrun_id)
            if orm_hpcrun is None:
                raise Exception(f"HpcRun with id {hpcrun_id} not found in the database")
            orm_hpcrun.status = JobStatusDB(new_slurm_job.job_state.lower())
            if new_slurm_job.start_time is not None and new_slurm_job.start_time != orm_hpcrun.start_time:
                orm_hpcrun.start_time = datetime.datetime.fromisoformat(new_slurm_job.start_time)
            if new_slurm_job.end_time is not None and new_slurm_job.end_time != orm_hpcrun.end_time:
                orm_hpcrun.end_time = datetime.datetime.fromisoformat(new_slurm_job.end_time)
            await session.flush()

    @override
    async def get_hpcrun_id_by_correlation_id(self, correlation_id: str) -> int | None:
        async with self.async_sessionmaker() as session, session.begin():
            stmt = select(ORMHpcRun.id).where(ORMHpcRun.correlation_id == correlation_id).limit(1)
            result: Result[tuple[int]] = await session.execute(stmt)
            orm_hpcrun_id: int | None = result.scalar_one_or_none()
            return orm_hpcrun_id

    @override
    async def close(self) -> None:
        pass
