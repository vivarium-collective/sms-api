from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from testcontainers.mongodb import MongoDbContainer  # type: ignore [import-untyped]

MONGODB_DATABASE_NAME = "mydatabase"
MONGODB_COLLECTION_NAME = "mycollection"


@pytest.fixture(scope="session")
def mongodb_container() -> MongoDbContainer:
    with MongoDbContainer() as container:
        container.start()
        yield container


@pytest_asyncio.fixture(scope="function")
async def mongo_test_client(mongodb_container: MongoDbContainer) -> AsyncGenerator[AsyncMongoClient, None]:  # type: ignore [type-arg]
    mongo_test_client: AsyncMongoClient = AsyncMongoClient(mongodb_container.get_connection_url())  # type: ignore [type-arg]
    yield mongo_test_client
    await mongo_test_client.close()


@pytest_asyncio.fixture(scope="function")
async def mongo_test_database(mongo_test_client: AsyncMongoClient) -> AsyncDatabase:  # type: ignore [type-arg]
    test_database: AsyncDatabase = mongo_test_client.get_database(name=MONGODB_DATABASE_NAME)  # type: ignore [type-arg]
    return test_database


@pytest_asyncio.fixture(scope="function")
async def mongo_test_collection(mongo_test_database: AsyncDatabase) -> AsyncCollection:  # type: ignore [type-arg]
    test_collection: AsyncCollection = mongo_test_database.get_collection(name=MONGODB_COLLECTION_NAME)  # type: ignore [type-arg]
    return test_collection
