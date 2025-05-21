import pickle
from typing import Any
from dataclasses import dataclass as dc, field
import copy

import numpy as np


@dc 
class BinaryData:
    value: str 

    def hydrate(self):
        return from_binary(self.value)


@dc
class SafeData:
    _hist: Any = field(default_factory=dict)

    @property
    def history(self):
        return self._hist
    
    @history.setter
    def history(self, v):
        raise Exception("Use the .set method instead!")

    def set(self, name, val, key):
        asbinary = to_binary(val)
        enc = encrypt(asbinary, key)
        self._hist[name] = enc

    def get(self, name, key):
        v = self.history[name]
        return decrypt(v, key)

    def remove(self, name):
        del self.history[name]

    def flush(self):
        c = copy.deepcopy(self.history)
        for k, v in c.items():
            self.remove(k)
        del c
        

def rand_bit(thresh: float = 0.3) -> str:
    return str(int(np.random.random() > thresh))

    
def to_binary(obj) -> str:
    return ''.join(f'{byte:08b}' for byte in pickle.dumps(obj))


def from_binary(binary_str: str):
    # Split into 8-bit chunks and convert each to a byte
    byte_chunks = [int(binary_str[i:i+8], 2) for i in range(0, len(binary_str), 8)]
    byte_data = bytes(byte_chunks)
    return pickle.loads(byte_data)


def binarize_message(data: Any) -> str:
    return to_binary(data)
    

def generate_key(msg_binary: str) -> str:
    binary_str = msg_binary
    size = len(binary_str)
    key = ''
    for i in range(size):
        key += rand_bit()
    return key


def encrypt(msg: Any, key: str):
    if not isinstance(msg, str):
        msg = to_binary(msg)
        
    zipped = zip_bits(msg, key)
    encrypted = ''
    for a, b in zipped:
        encrypted += str(xor(a, b))
    return encrypted
    

def decrypt(enc: str, key: str):
    zipped = zip_bits(enc, key)
    msg = ''
    for a, b in zipped:
        msg += str(xor(a, b))
    return from_binary(msg)


def xor(a: int, b: int) -> int:
    return 0 if a == b else 1


# noinspection PyTypeChecker
def zip_bits(msg: str, pad: str) -> tuple[int, int]:
    split_msg, split_pad = tuple(list(map(
        lambda arr: [bit for bit in arr],
        [msg, pad]
    )))

    return tuple(zip(split_msg, split_pad))


data = "5f0c7127-3be9-4488-b801-c7b6415b45e9"
msg = binarize_message(data)
key = generate_key(msg)
enc = encrypt(msg, key)