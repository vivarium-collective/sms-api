"""
====================
Connection Managers:
====================

Connection managers for the following:

- MongoDb (simulation runs)
- Sqlite/Postgres (keys, auth, users, etc)

"""

import abc
from dataclasses import dataclass

from bson import Binary
from gridfs.asynchronous import AsyncGridFS
from pymongo import AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from sqlalchemy import Engine, create_engine, text

# from vivarium.vivarium import Vivarium
from sms_api.data_model.base import BaseClass

VIVARIUM_INSTANCE_COLLECTION_NAME = "vivarium"


class DbManager(abc.ABC):
    def __init__(self, url: str):
        self.url = url

    @property
    @abc.abstractmethod
    def engine(self):
        pass

    @abc.abstractmethod
    async def read(self, *args, **kwargs):
        pass

    @abc.abstractmethod
    async def write(self, *args, **kwargs):
        pass


class MongoManager(DbManager):
    _collection_names = ["vivarium_instances", "simulation_runs"]

    def __init__(self, url: str | None = None):
        self.url = url or "mongodb://localhost:27017/"
        self.fs = AsyncGridFS(self.get_db())

    @property
    def engine(self) -> AsyncMongoClient:
        return AsyncMongoClient(self.url)

    def get_db(self, db_name: str = "simulations"):
        return self.engine[db_name]

    async def read(self, collection_name: str, query: dict, db_name: str = "simulations"):
        db = self.get_db(db_name)
        result = await db[collection_name].find_one(query)
        return result

    async def write(self, collection_name: str, data: dict, db_name: str = "simulations"):
        db = self.get_db(db_name)
        result = await db[collection_name].insert_one(data)
        return result

    async def view(self, collection_name: str, db_name: str = "simulations") -> list[dict]:
        db = self.get_db(db_name)
        collection: AsyncCollection = db.get_collection(collection_name)
        return [d for d in collection.find()]


class SqlManager(DbManager):
    _default_url = "sqlite+pysqlite:///:memory:"

    def __init__(self, url: str | None = None):
        self.url = url or self._default_url

    @property
    def engine(self) -> Engine:
        return create_engine(self.url)

    def new_table(self, tablename: str, schema: str):
        """
        :param schema: (`str`) string representation of a schema tuple. For example: "x int, y int"
        """
        with self.engine.connect() as conn:
            conn.execute(text(f"CREATE TABLE {tablename} {schema}"))
            conn.commit()

    async def read(self, tablename: str, query: str):
        pass

    async def write(self, tablename: str, values):
        pass


@dataclass
class VivariumRecord(BaseClass):
    vivarium_id: str
    instance: Binary


# def package_vivarium(vivarium_id: str):  # instance: Vivarium):
#     """Package/prepare vivarium instance for storage."""
#     return VivariumRecord(vivarium_id, Binary(pickle.dumps(instance)))
#
#
# async def write_vivarium(
#     vivarium_id: str,
#     # instance: Vivarium,
#     manager: MongoManager,
# ):
#     record = package_vivarium(vivarium_id, instance)
#     conf = await manager.write(VIVARIUM_INSTANCE_COLLECTION_NAME, record.to_dict())
#     return conf
#
#
# async def read_vivarium(vivarium_id: str, manager: MongoManager):
#     read = await manager.read(VIVARIUM_INSTANCE_COLLECTION_NAME, {"vivarium_id": vivarium_id})
#     if read is not None:
#         instance = read.get("instance")
#         return pickle.loads(instance)
#     else:
#         raise OSError(f"{vivarium_id} not found in vivarium ids. Check and try again.")
#
#
# def test_vivarium_io():
#     from asyncio import run
#
#     # v = Vivarium()
#     v_id = "test"
#     manager = MongoManager()
#     conf = run(write_vivarium(v_id, v, manager))
#     assert conf is not None
#     record = run(read_vivarium(v_id, manager))
#     assert "make_document" in dir(record)
#     print(record)
