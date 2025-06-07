import dataclasses as dc
import os
from ast import literal_eval

import dotenv as de
from common.encryption.keydist import UserDb
from fastapi import HTTPException, Request

from sms_api.data_model.base import BaseClass

de.load_dotenv()


@dc.dataclass
class UserMetadata(BaseClass):
    name: str
    location: str | None = None


@dc.dataclass
class UserKey(BaseClass):
    # public: str
    # private: str
    metadata: UserMetadata
    password: str


@dc.dataclass
class KeyData(BaseClass):
    main: list[UserKey] = dc.field(default_factory=list)
    dev: list[UserKey] = dc.field(default_factory=list)
    prod: list[UserKey] = dc.field(default_factory=list)
    example: list[UserKey] = dc.field(default_factory=list)


@dc.dataclass
class Users(BaseClass):
    main: list[UserMetadata] = dc.field(default_factory=list)
    dev: list[UserMetadata] = dc.field(default_factory=list)
    prod: list[UserMetadata] = dc.field(default_factory=list)
    example: list[UserMetadata] = dc.field(default_factory=list)


class ApiKeyDB:
    _example_users = [
        UserMetadata(name="test-user", location="LOCAL"),
        UserMetadata(name="Bob"),
        UserMetadata(name="Anita"),
    ]
    _keys = literal_eval(os.getenv("EXAMPLE_KEYS", "[]"))
    _example_keys = [UserKey(u, k) for u, k in list(zip(_example_users, _keys))]
    users = Users(main=_example_users)
    api_keys = KeyData(main=_example_keys)

    def add_user(self, username: str, key: str, scope: str = "main"):
        # create metadata
        metadata_u = UserMetadata(name=username)
        if not self.find_user(username):
            user_coll = self._get_users(scope)
            user_coll.append(metadata_u)

        # add key
        k = UserKey(metadata_u, key)
        coll = self._get_keys(scope)
        return coll.append(k)

    def check_key(self, key: str, scope: str = "main") -> bool:
        keys: list[UserKey] = self._get_keys(scope)
        return any([key == k.password for k in keys])

    def remove_user(self, name: str, scope: str = "main"):
        keys = self._get_keys(scope)
        users = self._get_users(scope)
        user = self.find_user(name, scope)
        if user is not None:
            keys.remove(user)
            users.remove(user.metadata)

    def find_user(self, name: str, scope: str = "main") -> UserKey | None:
        keys: list[UserKey] = self._get_keys(scope)
        user = None
        for k in keys:
            user_k = k.metadata
            if name == user_k.name:
                user = k
        return user

    def get_metadata_from_api_key(self, api_key: str, scope: str = "main") -> UserMetadata | None:
        keys: list[UserKey] = self._get_keys(scope)
        user = None
        for keydata in keys:
            if api_key == keydata.password:
                user = keydata.metadata
        return user

    def _get_keys(self, scope: str = "main") -> list[UserKey]:
        return getattr(self.api_keys, scope)

    def _get_users(self, scope: str = "main"):
        return getattr(self.users, scope)


def check_api_key(api_key: str, scope: str = "main"):
    valid = key_db.check_key(api_key, scope)
    if not valid:
        raise ValueError(f"API key {api_key} not found!")
    return valid


def get_user_from_api_key(api_key: str, scope: str = "main") -> UserMetadata | None:
    return key_db.get_metadata_from_api_key(api_key, scope)


async def fetch_user(request: Request, cookie: str = "session_user"):
    username = request.cookies.get(cookie)
    if not username:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": username}


key_db = ApiKeyDB()
user_db = UserDb()
