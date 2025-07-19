import logging
from pathlib import Path
from typing import Any

import nats
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sms_api.common.hpc.slurm_service import SlurmService
from sms_api.common.ssh.ssh_service import SSHService
from sms_api.config import get_settings
from sms_api.log_config import setup_logging
from sms_api.simulation.data_service import DataService, DataServiceHpc
from sms_api.simulation.database_service import DatabaseService, DatabaseServiceSQL
from sms_api.simulation.job_scheduler import JobScheduler
from sms_api.simulation.simulation_service import SimulationService, SimulationServiceHpc
from sms_api.simulation.tables_orm import create_db

logger = logging.getLogger(__name__)
setup_logging(logger)


def verify_service(service: DatabaseService | DataService | SimulationService | None) -> None:
    if service is None:
        logger.error(f"{service.__module__} is not initialized")
        raise HTTPException(status_code=500, detail=f"{service.__module__} is not initialized")


# ------- postgres database service (standalone or pytest) ------

global_postgres_engine: AsyncEngine | None = None


def set_postgres_engine(engine: AsyncEngine | None) -> None:
    global global_postgres_engine
    global_postgres_engine = engine


def get_postgres_engine() -> AsyncEngine | None:
    global global_postgres_engine
    return global_postgres_engine


# ------- simulation database service (standalone or pytest) ------

global_database_service: DatabaseService | None = None


def set_database_service(database_service: DatabaseService | None) -> None:
    global global_database_service
    global_database_service = database_service


def get_database_service() -> DatabaseService | None:
    global global_database_service
    return global_database_service


# ------- simulation service (standalone or pytest) ------

global_simulation_service: SimulationService | None = None


def set_simulation_service(simulation_service: SimulationService | None) -> None:
    global global_simulation_service
    global_simulation_service = simulation_service


def get_simulation_service() -> SimulationService | None:
    global global_simulation_service
    return global_simulation_service


# ------ job scheduler (standalone) -----------------------------

global_job_scheduler: JobScheduler | None = None


def set_job_scheduler(job_scheduler: JobScheduler | None) -> None:
    global global_job_scheduler
    global_job_scheduler = job_scheduler


def get_job_scheduler() -> JobScheduler | None:
    global global_job_scheduler
    return global_job_scheduler


# ------ data service (standalone or pytest) ------------------

global_data_service: DataService | None = None


def set_data_service(data_service: DataService | None) -> None:
    global global_data_service
    global_data_service = data_service


def get_data_service() -> DataService | None:
    global global_data_service
    return global_data_service


# ------ initialized standalone application (standalone) ------


def get_async_engine(url: str, enable_ssl: bool = True, **engine_params: Any) -> AsyncEngine:
    if not enable_ssl:
        engine_params["connect_args"] = {"ssl": "disable"}
    return create_async_engine(url, **engine_params)


async def init_standalone(enable_ssl: bool = True) -> None:
    _settings = get_settings()

    # set services that don't require params (currently using hpc)
    set_simulation_service(SimulationServiceHpc())
    set_data_service(DataServiceHpc())

    PG_USER = _settings.postgres_user
    PG_PSWD = _settings.postgres_password
    PG_DATABASE = _settings.postgres_database
    PG_HOST = _settings.postgres_host
    PG_PORT = _settings.postgres_port
    PG_POOL_SIZE = _settings.postgres_pool_size
    PG_MAX_OVERFLOW = _settings.postgres_max_overflow
    PG_POOL_TIMEOUT = _settings.postgres_pool_timeout
    PG_POOL_RECYCLE = _settings.postgres_pool_recycle
    if not PG_USER or not PG_PSWD or not PG_DATABASE or not PG_HOST or not PG_PORT:
        raise ValueError("Postgres connection settings are not properly configured.")
    postgres_url = f"postgresql+asyncpg://{PG_USER}:{PG_PSWD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
    engine = get_async_engine(
        url=postgres_url,
        enable_ssl=enable_ssl,
        echo=True,
        pool_size=PG_POOL_SIZE,
        max_overflow=PG_MAX_OVERFLOW,
        pool_timeout=PG_POOL_TIMEOUT,
        pool_recycle=PG_POOL_RECYCLE,
    )
    logging.warning("calling create_db() to initialize the database tables")
    await create_db(engine)
    set_postgres_engine(engine)

    database = DatabaseServiceSQL(engine)
    set_database_service(database)

    settings = get_settings()
    ssh_service = SSHService(
        hostname=settings.slurm_submit_host,
        username=settings.slurm_submit_user,
        key_path=Path(settings.slurm_submit_key_path),
        known_hosts=Path(settings.slurm_submit_known_hosts) if settings.slurm_submit_known_hosts else None,
    )
    slurm_service = SlurmService(ssh_service=ssh_service)

    nats_client = await nats.connect(_settings.nats_url)
    job_scheduler = JobScheduler(nats_client=nats_client, database_service=database, slurm_service=slurm_service)
    set_job_scheduler(job_scheduler)


async def shutdown_standalone() -> None:
    mongodb_service = get_database_service()
    if mongodb_service:
        await mongodb_service.close()

    engine = get_postgres_engine()
    if engine:
        await engine.dispose()

    set_simulation_service(None)
    set_database_service(None)
    set_data_service(None)

    job_scheduler = get_job_scheduler()
    if job_scheduler:
        await job_scheduler.close()
        set_job_scheduler(None)
