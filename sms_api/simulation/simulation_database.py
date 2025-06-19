import logging
from abc import ABC, abstractmethod

from sqlalchemy import Result, and_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from typing_extensions import override

from sms_api.simulation.models import (
    EcoliSimulation,
    EcoliSimulationRequest,
    HpcRun,
    ParcaDataset,
    ParcaDatasetRequest,
    SimulatorVersion,
)
from sms_api.simulation.tables_orm import ORMHpcRun, ORMParcaDataset, ORMSimulation, ORMSimulator

logger = logging.getLogger(__name__)


class SimulationDatabaseService(ABC):
    @abstractmethod
    async def insert_simulator(self, git_commit_hash: str, git_repo_url: str, git_branch: str) -> SimulatorVersion:
        pass

    @abstractmethod
    async def get_simulator(self, simulator_id: int) -> SimulatorVersion | None:
        pass

    @abstractmethod
    async def delete_simulator(self, simulator_id: int) -> None:
        pass

    @abstractmethod
    async def list_simulators(self) -> list[SimulatorVersion]:
        pass

    @abstractmethod
    async def get_hpcrun_by_slurmjobid(self, slurmjobid: int) -> HpcRun | None:
        pass

    @abstractmethod
    async def get_hpcrun(self, hpcrun_id: int) -> HpcRun | None:
        pass

    @abstractmethod
    async def get_or_insert_parca_dataset(self, parca_dataset_request: ParcaDatasetRequest) -> ParcaDataset:
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
    async def close(self) -> None:
        pass


class SimulationDatabaseServiceSQL(SimulationDatabaseService):
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
        stmt1 = select(ORMHpcRun).where(ORMHpcRun.id == slurmjobid).limit(1)
        result1: Result[tuple[ORMHpcRun]] = await session.execute(stmt1)
        orm_hpc_job: ORMHpcRun | None = result1.scalars().one_or_none()
        return orm_hpc_job

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
            return SimulatorVersion(
                database_id=new_orm_simulator.id,
                git_commit_hash=new_orm_simulator.git_commit_hash,
                git_repo_url=new_orm_simulator.git_repo_url,
                git_branch=new_orm_simulator.git_branch,
            )

    @override
    async def get_simulator(self, simulator_id: int) -> SimulatorVersion | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_simulator = await self._get_orm_simulator(session, simulator_id=simulator_id)
            if orm_simulator is None:
                return None
            return SimulatorVersion(
                database_id=orm_simulator.id,
                git_commit_hash=orm_simulator.git_commit_hash,
                git_repo_url=orm_simulator.git_repo_url,
                git_branch=orm_simulator.git_branch,
            )

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
                simulator_versions.append(
                    SimulatorVersion(
                        database_id=orm_simulator.id,
                        git_commit_hash=orm_simulator.git_commit_hash,
                        git_repo_url=orm_simulator.git_repo_url,
                        git_branch=orm_simulator.git_branch,
                    )
                )
            return simulator_versions

    @override
    async def get_hpcrun_by_slurmjobid(self, slurmjobid: int) -> HpcRun | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_hpc_job: ORMHpcRun | None = await self._get_orm_hpcrun_by_slurmjobid(session, slurmjobid=slurmjobid)
            if orm_hpc_job is None:
                return None
            return HpcRun(
                database_id=orm_hpc_job.id,
                slurmjobid=orm_hpc_job.slurmjobid,
                status=orm_hpc_job.status.to_job_status(),
                start_time=str(orm_hpc_job.start_time) if orm_hpc_job.start_time else None,
                end_time=str(orm_hpc_job.end_time) if orm_hpc_job.end_time else None,
                error_message=orm_hpc_job.error_message,
            )

    @override
    async def get_hpcrun(self, hpcrun_id: int) -> HpcRun | None:
        async with self.async_sessionmaker() as session, session.begin():
            orm_hpc_job: ORMHpcRun | None = await self._get_orm_hpcrun(session, hpcrun_id=hpcrun_id)
            if orm_hpc_job is None:
                return None
            return HpcRun(
                database_id=orm_hpc_job.id,
                slurmjobid=orm_hpc_job.slurmjobid,
                status=orm_hpc_job.status.to_job_status(),
                start_time=str(orm_hpc_job.start_time) if orm_hpc_job.start_time else None,
                end_time=str(orm_hpc_job.end_time) if orm_hpc_job.end_time else None,
                error_message=orm_hpc_job.error_message,
            )

    @override
    async def get_or_insert_parca_dataset(self, parca_dataset_request: ParcaDatasetRequest) -> ParcaDataset:
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
                hpc_run: HpcRun | None = (
                    await self.get_hpcrun(hpcrun_id=existing_orm_parca_dataset.hpcrun_id)
                    if existing_orm_parca_dataset.hpcrun_id
                    else None
                )
                simulator_version: SimulatorVersion | None = await self.get_simulator(
                    existing_orm_parca_dataset.simulator_id
                )
                if simulator_version is None:
                    raise Exception(
                        f"Simulator with id {existing_orm_parca_dataset.simulator_id} not found in the database"
                    )
                return ParcaDataset(
                    database_id=existing_orm_parca_dataset.id,
                    parca_dataset_request=ParcaDatasetRequest(
                        simulator_version=simulator_version,
                        parca_config=existing_orm_parca_dataset.parca_config,
                    ),
                    remote_archive_path=existing_orm_parca_dataset.remote_archive_path,
                    hpc_run=hpc_run,
                )
            else:
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
                    hpc_run=None,  # Initially set to None, can be updated later
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

            hpc_run: HpcRun | None = (
                await self.get_hpcrun(hpcrun_id=orm_parca_dataset.hpcrun_id) if orm_parca_dataset.hpcrun_id else None
            )
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
                hpc_run=hpc_run,
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
                hpc_run: HpcRun | None = (
                    await self.get_hpcrun(hpcrun_id=orm_parca_dataset.hpcrun_id)
                    if orm_parca_dataset.hpcrun_id
                    else None
                )
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
                        hpc_run=hpc_run,
                    )
                )
            return parca_datasets

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
    async def close(self) -> None:
        pass
