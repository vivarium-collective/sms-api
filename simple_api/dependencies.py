import logging
from pathlib import Path
from typing import Mapping
import warnings
import os

import dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from simple_api.common.database.db_utils import get_postgres_uri
from simple_api.config import get_settings
from simple_api.log_config import setup_logging
from simple_api.simulation.database_service import SimulationDatabaseService, SimulationDatabaseServiceSQL
from simple_api.simulation.simulation_service import SimulationService, SimulationServiceHpc
from simple_api.simulation.tables_orm import create_db


dotenv.load_dotenv('assets/dev/config/.dev_env')
logger = logging.getLogger(__name__)
setup_logging(logger)

# ------- postgres database service (standalone or pytest) ------

DEFAULT_POSTGRES_USER=os.getenv("USER")

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


# ------ initialized standalone application (standalone) ------


def get_postgres_vars() -> Mapping[str, str]:
    params = {}
    for k, v in os.environ.items():
      if "POSTGRES" in k:
        params[k] = v
    return params


def get_async_engine(enable_ssl: bool = True, **engine_params) -> AsyncEngine:
    if not enable_ssl:
        engine_params['connect_args'] = {"ssl": "disable"}
    return create_async_engine(**engine_params)


async def init_standalone(
        env_path: Path | None = None,
        enable_ssl: bool = False
) -> None:
    """
    NOTE: The following command works: `psql -h localhost -p 65432 -U alexanderpatrie sms` which is -> `psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER $POSTGRES_DB`
    :param env_path: (`Path`) Path to the environment file. If no value is passed, settings will be derived from `get_settings()`. See `get_settings` for more details. Defaults to `None`. 
    """
    def engine_params(**kwargs): return kwargs

    _settings = get_settings()

    if env_path:
        env_vars = get_postgres_vars()
        if dotenv.load_dotenv(env_path): 
            svars = vars()
            for k, v in svars.items():
                varname = k.upper()
                if varname in env_vars.keys():
                    new = env_vars[k] if isinstance(v, str) else int(env_vars[k])
                    setattr(_settings, k, new)
        else:
            raise FileNotFoundError(f'An env file could not be found at: {env_path}')

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
            connect_args={"ssl": "disable"} if not enable_ssl else {}
        )
    )

    warnings.warn("calling create_db() to initialize the database tables")
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

    # set_simulation_service(None)
    set_simulation_database_service(None)
