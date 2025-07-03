import logging
from typing import Callable

import nats
from fastapi import HTTPException
from nats.aio.client import Client as NATSClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sms_api.config import get_settings
from sms_api.log_config import setup_logging
from sms_api.simulation.data_service import DataService, DataServiceHpc
from sms_api.simulation.database_service import DatabaseService, DatabaseServiceSQL
from sms_api.simulation.job_scheduler import JobScheduler
from sms_api.simulation.simulation_service import SimulationService, SimulationServiceHpc
from sms_api.simulation.tables_orm import create_db

logger = logging.getLogger(__name__)
setup_logging(logger)


def verify_service(getter: Callable) -> Callable:
    def wrapper() -> DatabaseService | SimulationService | None:
        service = getter()
        if service is None:
            logger.error("Simulation database service is not initialized")
            raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
        else:
            return service

    return wrapper


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


@verify_service
def get_database_service() -> DatabaseService | None:
    global global_database_service
    return global_database_service


# ------- simulation service (standalone or pytest) ------

global_simulation_service: SimulationService | None = None


def set_simulation_service(simulation_service: SimulationService | None) -> None:
    global global_simulation_service
    global_simulation_service = simulation_service


@verify_service
def get_simulation_service() -> SimulationService | None:
    global global_simulation_service
    return global_simulation_service


# ------ nats client (standalone) -----------------------------

global_nats_client: NATSClient | None = None
global_job_scheduler: JobScheduler | None = None


# ------ data service (standalone or pytest) ------------------

global_data_service: DataService | None = None


def set_data_service(data_service: DataService | None) -> None:
    global global_data_service
    global_data_service = data_service


@verify_service
def get_data_service() -> DataService | None:
    global global_data_service
    return global_data_service


# ------ initialized standalone application (standalone) ------


def get_async_engine(enable_ssl: bool = True, **engine_params) -> AsyncEngine:
    if not enable_ssl:
        engine_params["connect_args"] = {"ssl": "disable"}
    return create_async_engine(**engine_params)


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
        echo=True,
        pool_size=PG_POOL_SIZE,
        max_overflow=PG_MAX_OVERFLOW,
        pool_timeout=PG_POOL_TIMEOUT,
        pool_recycle=PG_POOL_RECYCLE,
        enable_ssl=enable_ssl,
    )
    logging.warning("calling create_db() to initialize the database tables")
    await create_db(engine)
    set_postgres_engine(engine)

    database = DatabaseServiceSQL(engine)
    set_database_service(database)

    global global_nats_client
    global global_job_scheduler
    global_nats_client = await nats.connect(_settings.nats_url)
    global_job_scheduler = JobScheduler(nats_client=global_nats_client, database_service=database)

    await global_job_scheduler.subscribe()


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

    global global_nats_client
    if global_nats_client:
        await global_nats_client.close()
        global_nats_client = None
