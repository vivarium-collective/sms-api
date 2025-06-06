from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase


def configure_mongo(uri: str | None = None):
    MONGO_URI = uri or "mongodb://localhost:27017/"
    client = AsyncMongoClient(MONGO_URI)
    db: AsyncDatabase = client.get_database("simulations")
    return client, db
