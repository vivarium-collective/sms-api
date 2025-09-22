import datetime
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping

from sqlalchemy import Result, and_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import InstrumentedAttribute
from typing_extensions import override

from sms_api.common.hpc.models import SlurmJob
from sms_api.data.models import AnalysisConfig, ExperimentAnalysisDTO
from sms_api.simulation.models import (
    EcoliExperimentDTO,
    EcoliExperimentRequestDTO,
    EcoliSimulation,
    EcoliSimulationDTO,
    EcoliSimulationRequest,
    ExperimentMetadata,
    HpcRun,
    JobType,
    ParcaDataset,
    ParcaDatasetRequest,
    SimulationConfiguration,
    SimulatorVersion,
    WorkerEvent,
)
from sms_api.simulation.tables_orm import (
    JobStatusDB,
    JobTypeDB,
    ORMAnalysis,
    ORMEcoliExperiment,
    ORMEcoliSimulation,
    ORMHpcRun,
    ORMParcaDataset,
    ORMSimulation,
    ORMSimulationConfig,
    ORMSimulator,
    ORMWorkerEvent,
)

logger = logging.getLogger(__name__)


class DatabaseService(ABC):
    @abstractmethod
    async def insert_ecoli_experiment(
        self, config: SimulationConfiguration, metadata: ExperimentMetadata, last_updated: str
    ) -> EcoliSimulationDTO:
        pass

    @abstractmethod
    async def get_ecoli_experiment(self, database_id: int) -> EcoliSimulationDTO:
        pass

    @abstractmethod
    async def insert_analysis(
        self,
        name: str,
        config: AnalysisConfig,
        last_updated: str,
    ) -> ExperimentAnalysisDTO:
        pass

    @abstractmethod
    async def get_analysis(self, database_id: int) -> ExperimentAnalysisDTO:
        pass

    @abstractmethod
    async def insert_experiment(
        self,
        experiment_id: str,
        experiment_tag: str,
        metadata: Mapping[str, str],
        request: EcoliExperimentRequestDTO,
        last_updated: str,
    ) -> EcoliExperimentDTO:
        pass

    @abstractmethod
    async def get_experiment(self, experiment_id: str) -> EcoliExperimentDTO:
        pass

    @abstractmethod
    async def delete_experiment(self, experiment_id: str) -> bool:
        pass

    @abstractmethod
    async def list_experiments(self) -> list[EcoliExperimentDTO]:
        pass

    @abstractmethod
    async def get_simulation_config(self, config_id: str) -> SimulationConfiguration:
        pass

    @abstractmethod
    async def insert_simulation_config(
        self, config_id: str, config: SimulationConfiguration
    ) -> SimulationConfiguration:
        pass

    @abstractmethod
    async def delete_simulation_config(self, config_id: str) -> bool:
        pass

    @abstractmethod
    async def list_simulation_configs(self) -> list[SimulationConfiguration]:
        pass

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
    async def insert_simulation(self, sim_request: EcoliSimulationRequest) -> EcoliSimulation:
        pass

    @abstractmethod
    async def get_simulation(self, simulation_id: int) -> EcoliSimulation | None:
        pass

    @abstractmethod
    async def delete_simulation(self, simulation_id: int) -> None:
        pass

    @abstractmethod
    async def list_simulations(self) -> list[EcoliSimulation]:
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

    def _get_job_type_ref(self, job_type: JobType) -> InstrumentedAttribute[int | None]:
        match job_type:
            case JobType.BUILD_IMAGE:
                return ORMHpcRun.jobref_simulator_id
            case JobType.PARCA:
                return ORMHpcRun.jobref_parca_dataset_id
            case JobType.SIMULATION:
                return ORMHpcRun.jobref_simulation_id

    async def _get_orm_hpcrun_by_ref(self, session: AsyncSession, ref_id: int, job_type: JobType) -> ORMHpcRun | None:
        reference = self._get_job_type_ref(job_type)
        stmt1 = select(ORMHpcRun).where(reference == ref_id).limit(1)
        result1: Result[tuple[ORMHpcRun]] = await session.execute(stmt1)
        orm_hpc_job: ORMHpcRun | None = result1.scalars().one_or_none()

        return orm_hpc_job

    async def _get_orm_simulation_config(self, session: AsyncSession, config_id: str) -> ORMSimulationConfig | None:
        stmt1 = select(ORMSimulationConfig).where(ORMSimulationConfig.id == config_id).limit(1)
        result1: Result[tuple[ORMSimulationConfig]] = await session.execute(stmt1)
        orm_sim_config: ORMSimulationConfig | None = result1.scalars().one_or_none()
        return orm_sim_config

    async def _get_orm_experiment(self, session: AsyncSession, experiment_id: str) -> ORMEcoliExperiment | None:
        stmt1 = select(ORMEcoliExperiment).where(ORMEcoliExperiment.id == experiment_id).limit(1)
        result1: Result[tuple[ORMEcoliExperiment]] = await session.execute(stmt1)
        orm_experiment: ORMEcoliExperiment | None = result1.scalars().one_or_none()
        return orm_experiment

    async def _get_orm_analysis(self, session: AsyncSession, database_id: int) -> ORMAnalysis | None:
        stmt1 = select(ORMAnalysis).where(ORMAnalysis.id == database_id).limit(1)
        result1: Result[tuple[ORMAnalysis]] = await session.execute(stmt1)
        orm_experiment: ORMAnalysis | None = result1.scalars().one_or_none()
        return orm_experiment

    async def _get_orm_ecoli_simulation(self, session: AsyncSession, database_id: int) -> ORMEcoliSimulation | None:
        stmt1 = select(ORMEcoliSimulation).where(ORMEcoliSimulation.id == database_id).limit(1)
        result1: Result[tuple[ORMEcoliSimulation]] = await session.execute(stmt1)
        orm_experiment: ORMEcoliSimulation | None = result1.scalars().one_or_none()
        return orm_experiment

    @override
    async def insert_ecoli_experiment(
        self, config: SimulationConfiguration, metadata: ExperimentMetadata, last_updated: str
    ) -> EcoliSimulationDTO:
        async with self.async_sessionmaker() as session, session.begin():
            orm_ecoli_experiment = ORMEcoliSimulation(
                config=config.model_dump(), experiment_metadata=metadata.model_dump(), last_updated=last_updated
            )
            session.add(orm_ecoli_experiment)
            await session.flush()
            return orm_ecoli_experiment.to_dto()

    @override
    async def get_ecoli_experiment(self, database_id: int) -> EcoliSimulationDTO:
        async with self.async_sessionmaker() as session, session.begin():
            orm_ecoli_simulation = await self._get_orm_ecoli_simulation(session, database_id=database_id)
            if orm_ecoli_simulation is None:
                raise RuntimeError(f"Experiment {database_id} not found")
            return orm_ecoli_simulation.to_dto()

    @override
    async def insert_analysis(
        self,
        name: str,
        config: AnalysisConfig,
        last_updated: str,
    ) -> ExperimentAnalysisDTO:
        async with self.async_sessionmaker() as session, session.begin():
            orm_analysis = ORMAnalysis(
                name=name,
                config=config.model_dump(),
                last_updated=last_updated,
            )
            session.add(orm_analysis)
            await session.flush()
            return orm_analysis.to_dto()

    @override
    async def get_analysis(self, database_id: int) -> ExperimentAnalysisDTO:
        async with self.async_sessionmaker() as session, session.begin():
            orm_analysis = await self._get_orm_analysis(session, database_id=database_id)
            if orm_analysis is None:
                raise RuntimeError(f"Experiment {database_id} not found")
            return orm_analysis.to_dto()

    @override
    async def insert_experiment(
        self,
        experiment_id: str,
        experiment_tag: str,
        metadata: Mapping[str, str],
        request: EcoliExperimentRequestDTO,
        last_updated: str,
    ) -> EcoliExperimentDTO:
        async with self.async_sessionmaker() as session, session.begin():
            orm_experiment = ORMEcoliExperiment(
                id=experiment_id,
                tag=experiment_tag,
                simulation_metadata=metadata,
                request=request.model_dump(),
                last_updated=last_updated,
            )
            session.add(orm_experiment)
            await session.flush()
            return orm_experiment.to_dto()

    @override
    async def get_experiment(self, experiment_id: str) -> EcoliExperimentDTO:
        async with self.async_sessionmaker() as session, session.begin():
            orm_experiment = await self._get_orm_experiment(session, experiment_id=experiment_id)
            if orm_experiment is None:
                raise RuntimeError(f"Experiment {experiment_id} not found")
            return orm_experiment.to_dto()

    @override
    async def delete_experiment(self, experiment_id: str) -> bool:
        async with self.async_sessionmaker() as session, session.begin():
            orm_exp: ORMEcoliExperiment | None = await self._get_orm_experiment(session, experiment_id=experiment_id)
            if orm_exp is None:
                raise Exception(f"Ecoli Experiment with id: {experiment_id} not found in the database")
            await session.delete(orm_exp)
            return True

    @override
    async def list_experiments(self) -> list[EcoliExperimentDTO]:
        async with self.async_sessionmaker() as session:
            stmt = select(ORMEcoliExperiment)
            result: Result[tuple[ORMEcoliExperiment]] = await session.execute(stmt)
            orm_experiments = result.scalars().all()

            experiment_versions: list[EcoliExperimentDTO] = []
            for experiment in orm_experiments:
                experiment_versions.append(experiment.to_dto())
            return experiment_versions

    @override
    async def get_simulation_config(self, config_id: str) -> SimulationConfiguration:
        async with self.async_sessionmaker() as session, session.begin():
            orm_sim_config = await self._get_orm_simulation_config(session, config_id=config_id)
            if orm_sim_config is None:
                raise RuntimeError(f"No simulation config with id {config_id} found")
            return orm_sim_config.to_dto()

    @override
    async def insert_simulation_config(
        self, config_id: str, config: SimulationConfiguration
    ) -> SimulationConfiguration:
        async with self.async_sessionmaker() as session, session.begin():
            orm_sim_config = ORMSimulationConfig(
                id=config_id,
                data=config.model_dump() if isinstance(config, SimulationConfiguration) else config,
            )
            session.add(orm_sim_config)
            await session.flush()
            return orm_sim_config.to_dto()

    @override
    async def delete_simulation_config(self, config_id: str) -> bool:
        async with self.async_sessionmaker() as session, session.begin():
            simconfig: ORMSimulationConfig | None = await self._get_orm_simulation_config(session, config_id=config_id)
            if simconfig is None:
                raise Exception(f"Simulation Config with id: {config_id} not found in the database")
            await session.delete(simconfig)
            return True

    @override
    async def list_simulation_configs(self) -> list[SimulationConfiguration]:
        async with self.async_sessionmaker() as session:
            stmt = select(ORMSimulationConfig)
            result: Result[tuple[ORMSimulationConfig]] = await session.execute(stmt)
            orm_configs = result.scalars().all()

            config_versions: list[SimulationConfiguration] = []
            for orm_config in orm_configs:
                config_versions.append(orm_config.to_dto())
            return config_versions

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
                raise RuntimeError("Parca Dataset with the same configuration already exists in the database")

            # did not find the parca dataset, so insert it
            orm_simulator: ORMSimulator | None = await self._get_orm_simulator(session, simulator_id=simulator_id)
            if orm_simulator is None:
                raise Exception(f"Simulator with id {simulator_id} not found in the database")
            orm_parca_dataset = ORMParcaDataset(
                simulator_id=orm_simulator.id,
                parca_config=parca_dataset_request.parca_config,
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
                parca_config=orm_parca_dataset.parca_config,
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
                    parca_config=orm_parca_dataset.parca_config,
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
                            parca_config=orm_parca_dataset.parca_config,
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

            # prepare the EcoliSimulation object to return
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
    async def insert_simulation(self, sim_request: EcoliSimulationRequest) -> EcoliSimulation:
        async with self.async_sessionmaker() as session, session.begin():
            orm_simulator: ORMSimulator | None = await self._get_orm_simulator(
                session, simulator_id=sim_request.simulator.database_id
            )
            if orm_simulator is None:
                raise Exception(f"Simulator with id {sim_request.simulator.database_id} not found in the database")

            orm_parca_dataset: ORMParcaDataset | None = await self._get_orm_parca_dataset(
                session, parca_dataset_id=sim_request.parca_dataset_id
            )
            if orm_parca_dataset is None:
                raise Exception(f"Parca Dataset with id {sim_request.parca_dataset_id} not found in the database")

            if orm_parca_dataset.simulator_id != orm_simulator.id:
                raise Exception(
                    f"Parca Dataset simulator mismatch, id={orm_simulator.id} and {sim_request.simulator.database_id}"
                )
            orm_simulation = ORMSimulation(
                simulator_id=orm_simulator.id,
                parca_dataset_id=orm_parca_dataset.id,
                variant_config=sim_request.variant_config,
                variant_config_hash=sim_request.variant_config_hash,
            )
            session.add(orm_simulation)
            await session.flush()  # Ensure the ORM object is inserted and has an ID

            # prepare the EcoliSimulation object to return
            simulator_version = SimulatorVersion(
                database_id=orm_simulator.id,
                git_commit_hash=orm_simulator.git_commit_hash,
                git_repo_url=orm_simulator.git_repo_url,
                git_branch=orm_simulator.git_branch,
            )
            sim_request = EcoliSimulationRequest(
                simulator=simulator_version,
                parca_dataset_id=orm_parca_dataset.id,
                variant_config=orm_simulation.variant_config,
            )
            simulation = EcoliSimulation(database_id=orm_simulation.id, sim_request=sim_request)
            return simulation

    @override
    async def get_simulation(self, simulation_id: int) -> EcoliSimulation | None:
        async with self.async_sessionmaker() as session:
            orm_simulation: ORMSimulation | None = await self._get_orm_simulation(session, simulation_id)
            if orm_simulation is None:
                return None

            orm_simulator: ORMSimulator | None = await self._get_orm_simulator(
                session, simulator_id=orm_simulation.simulator_id
            )
            if orm_simulator is None:
                raise Exception(f"Simulator with id {orm_simulation.simulator_id} not found in the database")

            # Prepare the EcoliSimulation object to return
            simulator_version = SimulatorVersion(
                database_id=orm_simulation.simulator_id,
                git_commit_hash=orm_simulator.git_commit_hash,
                git_repo_url=orm_simulator.git_repo_url,
                git_branch=orm_simulator.git_branch,
            )
            sim_request = EcoliSimulationRequest(
                simulator=simulator_version,
                parca_dataset_id=orm_simulation.parca_dataset_id,
                variant_config=orm_simulation.variant_config,
            )
            simulation = EcoliSimulation(database_id=orm_simulation.id, sim_request=sim_request)
            return simulation

    @override
    async def delete_simulation(self, simulation_id: int) -> None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_simulation: ORMSimulation | None = await self._get_orm_simulation(session, simulation_id)
            if orm_simulation is None:
                raise Exception(f"Simulation with id {simulation_id} not found in the database")
            await session.delete(orm_simulation)

    @override
    async def list_simulations(self) -> list[EcoliSimulation]:
        async with self.async_sessionmaker() as session:
            stmt = select(ORMSimulation)
            result: Result[tuple[ORMSimulation]] = await session.execute(stmt)
            orm_simulations = result.scalars().all()

            simulations: list[EcoliSimulation] = []
            for orm_simulation in orm_simulations:
                orm_simulator: ORMSimulator | None = await self._get_orm_simulator(
                    session, simulator_id=orm_simulation.simulator_id
                )
                if orm_simulator is None:
                    raise Exception(f"Simulator with id {orm_simulation.simulator_id} not found in the database")

                # Prepare the EcoliSimulation object to return
                simulator_version = SimulatorVersion(
                    database_id=orm_simulator.id,
                    git_commit_hash=orm_simulator.git_commit_hash,
                    git_repo_url=orm_simulator.git_repo_url,
                    git_branch=orm_simulator.git_branch,
                )
                sim_request = EcoliSimulationRequest(
                    simulator=simulator_version,
                    parca_dataset_id=orm_simulation.parca_dataset_id,
                    variant_config=orm_simulation.variant_config,
                )
                simulation = EcoliSimulation(database_id=orm_simulation.id, sim_request=sim_request)
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
