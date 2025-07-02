from passlib.hash import argon2
from pydantic import BaseModel
from pymongo import AsyncMongoClient

from sms_api.common.database.db_utils import get_mongo_uri


class ApiUser(BaseModel):
    username: str
    email: str
    hashed_pwd: str
    disabled: bool


AUTH_DB_NAME = "secure"


def get_mongo_client(uri: str | None = None) -> AsyncMongoClient:
    mongo_uri = uri or get_mongo_uri()
    return AsyncMongoClient(mongo_uri)


async def insert_user(user: ApiUser, uri: str | None = None):
    client = get_mongo_client(uri)
    userdb = client.get_database(AUTH_DB_NAME)
    return await userdb.users.insert_one(user.model_dump())


def hash_password(actual: str):
    return argon2.hash(actual)


def verify_password_hash(actual: str, hashed: str) -> bool:
    return argon2.verify(actual, hashed)
