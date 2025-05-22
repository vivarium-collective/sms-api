import websockets
import asyncio
import json 
import time
import sys 


async def run_client(experiment_id: str, duration: int, api_key: str, overwrite: bool = False, timeout=20.0, buffer=1.0, max_timeout: float = 50.0):
    uri = f"ws://localhost:8080/api/v1/core/run-simulation?experiment_id={experiment_id}&duration={duration}&overwrite={str(overwrite).lower()}"
    api_key = "test"
    headers = {
        "X-Community-API-Key": api_key
    }
    # headers = None
    i = 0
    async with websockets.connect(uri, additional_headers=headers) as websocket:
        try:
            while i < max_timeout:
                try:
                    # message = await asyncio.wait_for(websocket.recv(), timeout)
                    message = await websocket.recv()
                    data = json.loads(message)  
                    yield data 
                    await asyncio.sleep(buffer)
                except websockets.exceptions.ConnectionClosed:
                    print('Connection Closed!')
                    i += 1
        except TimeoutError as e:
            print(f'Timeout {timeout} reached')
    print('timeout reached')


async def main(experiment_id: str, duration: int):
    key = "test"
    async for msg in run_client(experiment_id, duration, key):
        print("Received JSON:", msg)


if __name__ == "__main__":
    experiment_id = sys.argv[1]
    duration = 3 
    if len(sys.argv) > 2:
        duration = sys.argv[2]

    asyncio.run(main(experiment_id, duration))

