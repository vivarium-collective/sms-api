import logging

import nats
from nats.aio.client import Client as NATSClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sms_api.config import get_settings
from sms_api.simulation.job_scheduler import JobScheduler
from sms_api.simulation.simulation_database import SimulationDatabaseService, SimulationDatabaseServiceSQL
from sms_api.simulation.simulation_service import SimulationService, SimulationServiceHpc
from sms_api.simulation.tables_orm import create_db

# ------- postgres database service (standalone or pytest) ------

global_postgres_engine: AsyncEngine | None = None


def set_postgres_engine(engine: AsyncEngine | None) -> None:
    global global_postgres_engine
    global_postgres_engine = engine


def get_postgres_engine() -> AsyncEngine | None:
    global global_postgres_engine
    return global_postgres_engine


# ------- simulation database service (standalone or pytest) ------

global_simulation_database_service: SimulationDatabaseService | None = None


def set_simulation_database_service(database_service: SimulationDatabaseService | None) -> None:
    global global_simulation_database_service
    global_simulation_database_service = database_service


def get_simulation_database_service() -> SimulationDatabaseService | None:
    global global_simulation_database_service
    return global_simulation_database_service


# ------- simulation service (standalone or pytest) ------

global_simulation_service: SimulationService | None = None


def set_simulation_service(simulation_service: SimulationService | None) -> None:
    global global_simulation_service
    global_simulation_service = simulation_service


def get_simulation_service() -> SimulationService | None:
    global global_simulation_service
    return global_simulation_service


# ------ nats client (standalone) -----------------------------

global_nats_client: NATSClient | None = None
global_job_scheduler: JobScheduler | None = None

# ------ initialized standalone application (standalone) ------


async def init_standalone() -> None:
    _settings = get_settings()
    set_simulation_service(SimulationServiceHpc())

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
    engine = create_async_engine(
        postgres_url,
        echo=True,
        pool_size=PG_POOL_SIZE,
        max_overflow=PG_MAX_OVERFLOW,
        pool_timeout=PG_POOL_TIMEOUT,
        pool_recycle=PG_POOL_RECYCLE,
    )
    logging.warn("calling create_db() to initialize the database tables")
    await create_db(engine)
    set_postgres_engine(engine)

    simulation_database = SimulationDatabaseServiceSQL(engine)
    set_simulation_database_service(simulation_database)

    global global_nats_client
    global global_job_scheduler
    global_nats_client = await nats.connect(_settings.nats_url)
    global_job_scheduler = JobScheduler(nats_client=global_nats_client, database_service=simulation_database)

    await global_job_scheduler.subscribe()


async def shutdown_standalone() -> None:
    mongodb_service = get_simulation_database_service()
    if mongodb_service:
        await mongodb_service.close()

    engine = get_postgres_engine()
    if engine:
        await engine.dispose()

    set_simulation_service(None)
    set_simulation_database_service(None)

    global global_nats_client
    if global_nats_client:
        await global_nats_client.close()
        global_nats_client = None
