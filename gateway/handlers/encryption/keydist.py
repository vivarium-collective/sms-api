import abc
import pickle
from typing import Any
import uuid

import numpy as np


class Seed:
    def __new__(cls):
        return np.random.random()

    @classmethod
    def set_state(cls, pos: int = 1, has_gauss: int = 0, cached_gaussian: float = 0.000002211):
        state = ('MT19937', cls.generate_state_keys(), pos, has_gauss, cached_gaussian)
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
        key = ''
        for i in range(size):
            key += rand_bit()
        return key

    def decrypt(self, encrypted_message: EncryptionActor) -> UnencryptedMessage:
        zipped = zip_bits(encrypted_message.value, self.value)
        msg = ''
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
        encrypted = ''
        for a, b in zipped:
            encrypted += str(xor(a, b))
        return encrypted


def to_binary(data) -> str:
    import pickle
    binary_blob = pickle.dumps(data)
    return ''.join(format(byte, '08b') for byte in binary_blob)


def from_binary(bit_string):
    import pickle
    bit_bytes = bytes(int(bit_string[i:i + 8], 2) for i in range(0, len(bit_string), 8))
    return pickle.loads(bit_bytes)


def rand_bit(thresh: float = 0.3) -> str:
    return str(int(Seed() > thresh))


def xor(a: int, b: int) -> int:
    return 0 if a == b else 1


# noinspection PyTypeChecker
def zip_bits(msg: str, pad: str) -> tuple[int, int]:
    split_msg, split_pad = tuple(list(map(
        lambda arr: [bit for bit in arr],
        [msg, pad]
    )))

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
    data = {'dna': np.random.random((11,)), 'mrna': {'x': 11.11, 'y': 22.22, 'z': 0.00001122}}
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


key, encrypted, hydrated = test_components()

