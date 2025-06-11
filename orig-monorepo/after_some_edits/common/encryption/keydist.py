import abc
import hashlib
import pickle
import uuid
from dataclasses import dataclass
from typing import Any
from warnings import warn

import numpy as np
import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from sms_api.data_model.base import BaseClass

__all__ = ["generate_keys", "User", "UserDb"]


class Seed:
    def __new__(cls):
        return np.random.random()

    @classmethod
    def set_state(cls, pos: int = 1, has_gauss: int = 0, cached_gaussian: float = 0.000002211):
        state = ("MT19937", cls.generate_state_keys(), pos, has_gauss, cached_gaussian)
        return np.random.set_state(state)

    @classmethod
    def generate_state_keys(cls, low: int = 1, high: int = 11):
        arr = np.random.randint(low, high, (624,))
        return np.asarray(arr, dtype=np.uint64)


# TODO: make a dedicated actor(key) that is instantiated by the vivarium interface for each object/store in the composition
# TODO: also make a dedicated actor for accessing the store itself: possibly just extend high-level cloud auth logic
class EncryptionActor(abc.ABC):
    value: str

    def __init__(self, *args):
        self.value = self._generator(*args)

    def pickle(self):
        return pickle.dumps(self.value)

    @abc.abstractmethod
    def _generator(self, *args):
        pass


class UnencryptedMessage(EncryptionActor):
    def __init__(self, data: Any):
        super().__init__(data)

    def _generator(self, data: Any):
        return to_binary(data)


class Key(EncryptionActor):
    def __init__(self, msg: UnencryptedMessage):
        super().__init__(msg)

    @staticmethod
    def _make_id():
        return str(uuid.uuid4())

    @property
    def id(self):
        return self._make_id()

    def _generator(self, msg: UnencryptedMessage):
        size = len(msg.value)
        key = ""
        for _i in range(size):
            key += rand_bit()
        return key

    def decrypt(self, encrypted_message: EncryptionActor) -> UnencryptedMessage:
        zipped = zip_bits(encrypted_message.value, self.value)
        msg = ""
        for a, b in zipped:
            msg += str(xor(a, b))
        return UnencryptedMessage(self.hydrate(msg))

    def hydrate(self, msg: str):
        return from_binary(msg)


class EncryptedMessage(EncryptionActor):
    def __init__(self, key: Key):
        super().__init__(key)

    def _generator(self, key: Key):
        zipped = zip_bits(key.message.value, key.value)
        encrypted = ""
        for a, b in zipped:
            encrypted += str(xor(a, b))
        return encrypted


def to_binary(data) -> str:
    import pickle

    binary_blob = pickle.dumps(data)
    return "".join(format(byte, "08b") for byte in binary_blob)


def from_binary(bit_string):
    import pickle

    bit_bytes = bytes(int(bit_string[i : i + 8], 2) for i in range(0, len(bit_string), 8))
    return pickle.loads(bit_bytes)


def rand_bit(thresh: float = 0.3) -> str:
    return str(int(Seed() > thresh))


def xor(a: int, b: int) -> int:
    return 0 if a == b else 1


# noinspection PyTypeChecker
def zip_bits(msg: str, pad: str) -> tuple[int, int]:
    split_msg, split_pad = tuple(list(map(lambda arr: [bit for bit in arr], [msg, pad])))

    return tuple(zip(split_msg, split_pad))


def get_key(data) -> Key:
    msg = UnencryptedMessage(data)
    return Key(msg)


def encrypt(key: Key) -> EncryptedMessage:
    return EncryptedMessage(key)


def decrypt(key: Key, encrypted: EncryptedMessage):
    decrypted = key.decrypt(encrypted)
    return from_binary(decrypted.value)


def test_components():
    import numpy as np

    data = {"dna": np.random.random((11,)), "mrna": {"x": 11.11, "y": 22.22, "z": 0.00001122}}
    key = get_key(data)
    encrypted = encrypt(key)
    hyrdated = decrypt(key, encrypted)
    return key, encrypted, hyrdated


def new_password() -> str:
    import hashlib

    import numpy as np

    root = str(np.random.random())
    passphrase = hashlib.sha256(root.encode()).hexdigest()
    msg = UnencryptedMessage(passphrase)
    key = Key(msg)
    pswrd_bits = f"0o{key.value}"
    return str(eval(pswrd_bits))


@dataclass
class Keys(BaseClass):
    # TODO: encrypt this further upon export
    private: str
    public: str

    def export_private(self, location: str):
        with open(location, "w") as f:
            f.write(self.private)

    def export_public(self, location: str):
        with open(location, "w") as f:
            f.write(self.public)


@dataclass
class User(BaseClass):
    username: str
    location: tuple | None = None
    keys: Keys | None = None

    def __post_init__(self):
        if self.location is None:
            self.location = get_location_coords()
        if not self.keys:
            self.keys = generate_keys(self)

    @property
    def authenticated(self) -> bool:
        return self.keys is not None

    @property
    def id(self) -> str:
        return f"{self.username}-{uuid.uuid4()!s}"

    @property
    def representation(self):
        return f"{self.id}{self.location}"

    def verify(self):
        return self.authenticated


@dataclass
class AuthenticatedUser(BaseClass):
    username: str
    id: str


class UserDb:
    users: list[AuthenticatedUser] = []
    keys: dict[str, Keys | None] = {}

    def add_user(self, user: User):
        assert user.verify(), "This client cannot be verified. Try adding public and private keys."
        self.users.append(AuthenticatedUser(username=user.username, id=user.id))
        self.keys[user.id] = user.keys

    def find_user(self, username: str):
        user = filter(lambda u: u.username == username, self.users)
        try:
            return next(user)
        except StopIteration:
            pass

    def remove_user(self, username: str):
        usr = self.find_user(username)
        if usr:
            self.users.remove(usr)
            self.keys.pop(usr.id, None)
        else:
            warn("That user could not be found", stacklevel=2)


def get_location_coords() -> tuple[float, float]:
    default = (0.0, 0.0)
    try:
        response = requests.get("https://ipinfo.io/json")
        data = response.json()
        loc = data.get("loc")  # Format: "lat,lng"
        if loc:
            lat, lng = map(float, loc.split(","))
            return (lat, lng)
        else:
            return default
    except Exception as e:
        print(f"Error getting location: {e}")
        return default


# def generate_client(username: str):
#     return Client(username=username, location=get_location_coords())  # type: ignore


def derive_private(secret_string: str | None = None, client: User | None = None) -> ec.EllipticCurvePrivateKey:
    secret_string = secret_string or client.representation if client else ""
    digest = hashlib.sha256(secret_string.encode()).digest()
    order = int("FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551", 16)
    private_value = int.from_bytes(digest, "big") % order
    if private_value == 0:
        raise ValueError("Invalid key: value must not be 0")

    return ec.derive_private_key(private_value, ec.SECP256R1(), default_backend())


def derive_pem(private_key: ec.EllipticCurvePrivateKey) -> Keys:
    # 🔒 Private key (PEM)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,  # RFC 5208
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    # 🔓 Public key (PEM)
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,  # RFC 5280
        )
        .decode()
    )

    return Keys(private=private_pem, public=public_pem)


def generate_keys(secret_string: str | None = None, client: User | None = None) -> Keys:
    private = derive_private(secret_string, client)
    return derive_pem(private)
