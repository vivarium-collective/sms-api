from typing import Any

from pymongo import AsyncMongoClient

from sms_api.config import get_settings
from sms_api.simulation.database import SimulationDatabaseService, SimulationDatabaseServiceMongo
from sms_api.simulation.simulation_service import SimulationService, SimulationServiceSlurm

# ------- database service (standalone or pytest) ------

global_database_service: SimulationDatabaseService | None = None


def set_database_service(database_service: SimulationDatabaseService | None) -> None:
    global global_database_service
    global_database_service = database_service


def get_database_service() -> SimulationDatabaseService | None:
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


# ------ initialized standalone application (standalone) ------


async def init_standalone() -> None:
    _settings = get_settings()
    set_simulation_service(SimulationServiceSlurm())

    mongo_client: AsyncMongoClient[dict[str, Any]] = AsyncMongoClient(get_settings().mongodb_uri)
    set_database_service(SimulationDatabaseServiceMongo(db_client=mongo_client))


async def shutdown_standalone() -> None:
    db_service = get_database_service()
    if db_service:
        await db_service.close()

    set_simulation_service(None)
    set_database_service(None)
