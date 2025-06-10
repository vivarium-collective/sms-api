from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from testcontainers.mongodb import MongoDbContainer

from sms_api.dependencies import get_database_service, set_database_service
from sms_api.simulation.database import SimulationDatabaseServiceMongo

MONGODB_DATABASE_NAME = "mydatabase"
MONGODB_COLLECTION_NAME = "mycollection"


@pytest.fixture(scope="session")
def mongodb_container() -> MongoDbContainer:
    with MongoDbContainer() as container:
        container.start()
        yield container


@pytest_asyncio.fixture(scope="function")
async def mongo_test_client(mongodb_container: MongoDbContainer) -> AsyncGenerator[AsyncMongoClient, None]:
    mongo_test_client = AsyncMongoClient(mongodb_container.get_connection_url())
    yield mongo_test_client
    mongo_test_client.close()


@pytest_asyncio.fixture(scope="function")
async def mongo_test_database(mongo_test_client: AsyncMongoClient) -> AsyncDatabase:
    test_database: AsyncDatabase = mongo_test_client.get_database(name=MONGODB_DATABASE_NAME)
    return test_database


@pytest_asyncio.fixture(scope="function")
async def mongo_test_collection(mongo_test_database: AsyncDatabase) -> AsyncCollection:
    test_collection: AsyncCollection = mongo_test_database.get_collection(name=MONGODB_COLLECTION_NAME)
    return test_collection


@pytest_asyncio.fixture(scope="function")
async def simulation_database_service_mongo(
    mongo_test_client: AsyncMongoClient,
) -> AsyncGenerator[SimulationDatabaseServiceMongo, None]:
    db_service = SimulationDatabaseServiceMongo(db_client=mongo_test_client)
    old_db_service = get_database_service()
    set_database_service(db_service)

    yield db_service

    set_database_service(old_db_service)
    # await db_service.close()  the underlying client will already be closed
