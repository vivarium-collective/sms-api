import base64
import gzip
import json
import redis


class Message(dict):
    def __new__(cls, *args, **kwargs):
        return cls.__new__(cls, *args, **kwargs)


def send_message(r: redis.Redis, dataname: str, data: dict):
    return r.hset(dataname, mapping=data)


def recieve_message(r: redis.Redis, dataname: str) -> Message:
    return Message(**r.hgetall(dataname))
    

def compress_message(data: dict) -> str:
    compressed = gzip.compress(json.dumps(data).encode())
    return base64.b64encode(compressed).decode()


def decompress_message(encoded_data: str) -> dict:
    compressed = base64.b64decode(encoded_data)
    decompressed = gzip.decompress(compressed).decode()
    return json.loads(decompressed)