import logging
import os
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import Callable

import dotenv
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from sms_api.config import Settings, get_settings
from sms_api.log_config import setup_logging
from sms_api.simulation.database_service import SimulationDatabaseService, SimulationDatabaseServiceSQL
from sms_api.simulation.simulation_service import SimulationService, SimulationServiceHpc
from sms_api.simulation.tables_orm import create_db


logger = logging.getLogger(__name__)
setup_logging(logger)

# ------- postgres database service (standalone or pytest) ------


global_postgres_engine: AsyncEngine | None = None


def verify_service(getter: Callable) -> Callable[[], SimulationDatabaseService | SimulationService | None]:
    def wrapper() -> SimulationDatabaseService | SimulationService | None:
        service = getter()
        if service is None:
            logger.error("Simulation database service is not initialized")
            raise HTTPException(status_code=500, detail="Simulation database service is not initialized")
        else:
            return service

    return wrapper


def set_postgres_engine(engine: AsyncEngine | None) -> None:
    global global_postgres_engine
    global_postgres_engine = engine


def get_postgres_engine() -> AsyncEngine | None:
    global global_postgres_engine
    return global_postgres_engine


# ------- simulation database service (standalone or pytest) ------

global_simulation_database_service: SimulationDatabaseService | None = None


def set_simulation_database_service(
    database_service: SimulationDatabaseService | None,
) -> None:
    global global_simulation_database_service
    global_simulation_database_service = database_service


@verify_service
def get_simulation_database_service() -> SimulationDatabaseService | None:
    global global_simulation_database_service
    return global_simulation_database_service


# ------- simulation service (standalone or pytest) ------

global_simulation_service: SimulationService | None = None


def set_simulation_service(simulation_service: SimulationService | None) -> None:
    global global_simulation_service
    global_simulation_service = simulation_service


@verify_service
def get_simulation_service() -> SimulationService | None:
    global global_simulation_service
    return global_simulation_service


# ------ initialized standalone application (standalone) ------


def get_postgres_vars() -> Mapping[str, str]:
    params = {}
    for k, v in os.environ.items():
        if "POSTGRES" in k:
            params[k] = v
    return params


def get_async_engine(enable_ssl: bool = True, **engine_params) -> AsyncEngine:
    if not enable_ssl:
        engine_params["connect_args"] = {"ssl": "disable"}
    return create_async_engine(**engine_params)


def update_from_env(_settings: Settings, env_path: Path | None = None):
    env_vars = get_postgres_vars()
    if dotenv.load_dotenv(env_path):
        settings_vars = vars(_settings)
        for attr_name, attr_val in settings_vars.items():
            setting_id = attr_name.upper()
            if setting_id in env_vars:
                new = env_vars.get(setting_id) if isinstance(attr_val, str) else int(env_vars[setting_id])
                setattr(_settings, attr_name, new)
    else:
        raise FileNotFoundError(f"An env file could not be found at: {env_path}")


async def init_standalone(enable_ssl: bool = True) -> None:
    """
    NOTE: The following command works: `psql -h localhost -p 65432 -U alexanderpatrie sms` which is ->
        `psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER $POSTGRES_DB`

    :param env_path: (`Path`) Path to the environment file. If no value is passed,
        settings will be derived from `get_settings()`. See `get_settings` for more details. Defaults to `None`.
    """
    # configure asnd set simulation service
    set_simulation_service(SimulationServiceHpc())

    # configure and set db engine service
    def engine_params(**kwargs):
        return kwargs

    _settings = get_settings()

    # if env_path:
    #     update_from_env(_settings, env_path)

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
        **engine_params(
            url=postgres_url,
            echo=True,
            pool_size=PG_POOL_SIZE,
            max_overflow=PG_MAX_OVERFLOW,
            pool_timeout=PG_POOL_TIMEOUT,
            pool_recycle=PG_POOL_RECYCLE,
            connect_args={"ssl": "disable"} if not enable_ssl else {},
        )
    )

    warnings.warn("calling create_db() to initialize the database tables", stacklevel=2)
    await create_db(engine)
    set_postgres_engine(engine)
    set_simulation_database_service(SimulationDatabaseServiceSQL(engine))


async def shutdown_standalone() -> None:
    mongodb_service = get_simulation_database_service()
    if mongodb_service:
        await mongodb_service.close()

    engine = get_postgres_engine()
    if engine:
        await engine.dispose()

    set_simulation_service(None)
    set_simulation_database_service(None)
