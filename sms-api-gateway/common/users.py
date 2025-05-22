from common.encryption.keydist import User, UserDb
import dataclasses as dc
from hashlib import sha256
import os

import dotenv as de

from data_model.base import BaseClass 


de.load_dotenv()

@dc.dataclass
class UserMetadata(BaseClass):
    name: str 


@dc.dataclass
class UserKeys(BaseClass):
    public: str
    private: str
    metadata: UserMetadata


@dc.dataclass
class KeyData(BaseClass):
    dev: dict[str, str] = dc.field(default_factory=dict)
    prod: dict[str, str] = dc.field(default_factory=dict)
    example: dict[str, str] = dc.field(default_factory=dict)

    @property 
    def all(self):
        return self.to_dict()
        

@dc.dataclass
class Users(BaseClass):
    dev: dict[str, UserMetadata] = dc.field(default_factory=dict)
    prod: dict[str, UserMetadata] = dc.field(default_factory=dict)
    example: dict[str, UserMetadata] = dc.field(default_factory=dict)


class ApiKeyDB:
    # {<PUBLIC KEY>: <PRIVATE KEY>}
    __example_keys = {
        "test": "test",
        "e54d4431-5dab-474e-b71a-0db1fcb9e659": "7oDYjo3d9r58EJKYi5x4E8",  # Bob
        "5f0c7127-3be9-4488-b801-c7b6415b45e9": "mUP7PpTHmFAkxcQLWKMY8t"  # Anita
    }
    __example_users = {
        "test": UserMetadata(name="test-key"),
        "7oDYjo3d9r58EJKYi5x4E8": UserMetadata(name="Test"),
        "mUP7PpTHmFAkxcQLWKMY8t": UserMetadata(name="Anita")
    }
    api_keys = KeyData(example=__example_keys, dev={}, prod={})
    users = Users({}, {}, __example_users)

    def add_api_key(self, username: str, key: str, dev: bool = False):
        metadata_u = UserMetadata(name=username)
        if dev:
            self.api_keys.dev[key] = key
            self.users.dev[username] = metadata_u
        else:
            self.api_keys.prod[key] = key
            self.users.prod[username] = metadata_u

    def add_api_keys(self, username: str, public: str, private: str, dev: bool = False):
        metadata_u = UserMetadata(name=username)
        if dev:
            self.api_keys.dev[public] = private
            self.users.dev[username] = metadata_u
        else:
            self.api_keys.prod[public] = private
            self.users.prod[username] = metadata_u
    
    def check_key(self, key: str, collection: str) -> bool:
        keys: dict = getattr(self.api_keys, collection)
        return key in keys
    
    def remove_api_key(self, public: str):
        self.api_keys.prod.pop(public, None)
    
    def add_user(self, scope: str, user: UserMetadata, private: str):
        self.users.to_dict()[scope][private] = user
    
    def remove_user(self, scope: str, name: str):
        table = self.users.to_dict()[scope]
        for private, user in table.items():
            if user.name == name:
                delattr(table, private)
    
    def get_table(self, scope: str):
        return self.api_keys.to_dict()[scope]


def check_api_key(api_key: str, scope: str = "example"):
    table = key_db.get_table(scope)
    return api_key in table


def get_user_from_api_key(api_key: str, scope: str = "example"):
    table: dict[str, UserMetadata] = key_db.users.to_dict()[scope]
    return table[key_db.get_table(scope)[api_key]]


def test_user_db():
    test_user = User(username="JoeyD")
    user_db.add_user(test_user)


key_db = ApiKeyDB()
user_db = UserDb()
