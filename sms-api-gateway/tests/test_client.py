import base64
import gzip
import traceback
import websockets
import asyncio
import json 
import time
import sys 


class Client(object):
    def __init__(self, uri_prefix: str):
        self.uri_prefix = uri_prefix

    @classmethod
    def compress_message(cls, data: dict) -> str:
        compressed = gzip.compress(json.dumps(data).encode())
        return base64.b64encode(compressed).decode()

    @classmethod
    def decompress_message(cls, encoded) -> dict:
        # Decode from base64
        compressed_bytes = base64.b64decode(encoded)
        
        # Decompress the gzip-compressed bytes
        decompressed_bytes = gzip.decompress(compressed_bytes)
        
        # Convert bytes back to JSON/dict
        return json.loads(decompressed_bytes.decode())

    async def run_simulation(self, experiment_id: str, duration: int, api_key: str, overwrite: bool = False, timeout=20.0, buffer=1.0, max_timeout: float = 50.0):
        uri = f"ws://localhost:8080/api/v1/core/run-simulation?experiment_id={experiment_id}&duration={duration}&overwrite={str(overwrite).lower()}"
        api_key = "test"
        headers = {
            "X-Community-API-Key": api_key
        }
        # headers = None
        i = 0
        async with websockets.connect(uri, additional_headers=headers) as websocket:
            while True:
                try:
                    # message = await asyncio.wait_for(websocket.recv(), timeout)
                    message = await websocket.recv()
                    data = Client.decompress_message(message)
                    # data = json.loads(message) 
                    yield data 
                    await asyncio.sleep(buffer)
                except websockets.exceptions.ConnectionClosed:
                    print('Connection Closed!')
                    traceback.print_exc()
                    break
        print('timeout reached')


async def main(experiment_id: str, duration: int):
    key = "test"
    uri_prefix = 'ws://localhost:8080/api/v1'
    async for msg in run_client(experiment_id, duration, key):
        print("Received JSON:", msg)


if __name__ == "__main__":
    experiment_id = sys.argv[1]
    duration = 3 
    if len(sys.argv) > 2:
        duration = sys.argv[2]

    asyncio.run(main(experiment_id, duration))

