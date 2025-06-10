import logging
from abc import ABC, abstractmethod
from typing import Any

from bson.objectid import ObjectId
from pymongo import AsyncMongoClient
from pymongo.results import InsertOneResult
from typing_extensions import override

from sms_api.config import get_settings
from sms_api.simulation.models import EcoliSimulation

logger = logging.getLogger(__name__)


class SimulationDatabaseService(ABC):
    @abstractmethod
    async def insert_simulation(self, simulation: EcoliSimulation) -> EcoliSimulation:
        pass

    @abstractmethod
    async def get_simulation(self, database_id: str) -> EcoliSimulation | None:
        pass

    @abstractmethod
    async def delete_simulation(self, database_id: str) -> None:
        pass

    @abstractmethod
    async def delete_all_simulations(self) -> None:
        pass

    @abstractmethod
    async def list_simulations(self) -> list[EcoliSimulation]:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass


class SimulationDatabaseServiceMongo(SimulationDatabaseService):
    def __init__(self, db_client: AsyncMongoClient[dict[str, Any]]) -> None:
        self._db_client = db_client
        database = self._db_client.get_database(get_settings().mongodb_database)
        self._simulation_col = database.get_collection(get_settings().mongodb_collection_omex)

    @override
    async def insert_simulation(self, simulation: EcoliSimulation) -> EcoliSimulation:
        if simulation.database_id is not None:
            raise Exception("Cannot insert document that already has a database id")
        logger.info(f"Inserting OMEX file with hash {simulation.file_hash_md5}")
        result: InsertOneResult = await self._simulation_col.insert_one(simulation.model_dump())
        if result.acknowledged:
            inserted_simulation: EcoliSimulation = simulation.model_copy(deep=True)
            inserted_simulation.database_id = str(result.inserted_id)
            return inserted_simulation
        else:
            raise Exception("Insert failed")

    # @lru_cache
    @override
    async def get_simulation(self, file_hash_md5: str) -> EcoliSimulation | None:
        logger.info(f"Getting OMEX file with hash {file_hash_md5}")
        document = await self._simulation_col.find_one({"file_hash_md5": file_hash_md5})
        if document is not None:
            doc_dict = dict(document)
            doc_dict["database_id"] = str(document["_id"])
            del doc_dict["_id"]
            return EcoliSimulation.model_validate(doc_dict)
        else:
            return None

    @override
    async def delete_simulation(self, database_id: str) -> None:
        logger.info(f"Deleting OMEX file with database_id {database_id}")
        result = await self._simulation_col.delete_one({"_id": ObjectId(database_id)})
        if result.deleted_count == 1:
            return
        else:
            raise Exception("Delete failed")

    @override
    async def delete_all_simulations(self) -> None:
        logger.info("Deleting all OMEX file records")
        result = await self._simulation_col.delete_many({})
        if not result.acknowledged:
            raise Exception("Delete failed")

    @override
    async def list_simulations(self) -> list[EcoliSimulation]:
        logger.info("listing OMEX files")
        simulations: list[EcoliSimulation] = []
        for document in await self._simulation_col.find().to_list(length=100):
            doc_dict = dict(document)
            doc_dict["database_id"] = str(document["_id"])
            del doc_dict["_id"]
            simulations.append(EcoliSimulation.model_validate(doc_dict))
        return simulations

    @override
    async def close(self) -> None:
        await self._db_client.close()
