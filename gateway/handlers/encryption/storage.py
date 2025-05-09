import dataclasses as dc
from hashlib import sha256

from api.data_model.base import BaseClass 


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


@dc.dataclass
class Users(BaseClass):
    dev: dict[str, UserMetadata] = dc.field(default_factory=dict)
    prod: dict[str, UserMetadata] = dc.field(default_factory=dict)
    example: dict[str, UserMetadata] = dc.field(default_factory=dict)


class ApiKeyDB:
    # {<PUBLIC KEY>: <PRIVATE KEY>}
    __example_keys = {
        "e54d4431-5dab-474e-b71a-0db1fcb9e659": "7oDYjo3d9r58EJKYi5x4E8",  # Bob
        "5f0c7127-3be9-4488-b801-c7b6415b45e9": "mUP7PpTHmFAkxcQLWKMY8t"  # Anita
    }
    __example_users = {
        "7oDYjo3d9r58EJKYi5x4E8": UserMetadata(name="Test"),
        "mUP7PpTHmFAkxcQLWKMY8t": UserMetadata(name="Anita")
    }
    api_keys = KeyData(example=__example_keys, dev={}, prod={})
    users = Users({}, {}, __example_users)

    def add_api_key(self, public: str, private: str):
        self.api_keys.prod[public] = private
    
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


key_db = ApiKeyDB()


def check_api_key(api_key: str, scope: str = "example"):
    table = key_db.get_table(scope)
    return api_key in table


def get_user_from_api_key(api_key: str, scope: str = "example"):
    table: dict[str, UserMetadata] = key_db.users.to_dict()[scope]
    return table[key_db.get_table(scope)[api_key]]
