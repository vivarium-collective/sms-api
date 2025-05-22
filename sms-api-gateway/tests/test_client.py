import websockets
import asyncio
import json 
import time
import sys 


async def run_client(experiment_id: str, duration: int, api_key: str, timeout=5.0, buffer=1.0):
    uri = f"ws://localhost:8080/api/v1/core/run-simulation?experiment_id={experiment_id}&duration={duration}"
    api_key = "test"
    headers = {
        "X-Community-API-Key": api_key
    }
    # headers = None
    async with websockets.connect(uri, additional_headers=headers) as websocket:
        try:
            while True:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout)
                    data = json.loads(message)  
                    yield data 
                    await asyncio.sleep(buffer)
                except websockets.exceptions.ConnectionClosed or TimeoutError:
                    print('Connection Closed!')
        except TimeoutError as e:
            print(f'Timeout {timeout} reached')


async def main(experiment_id: str, duration: int):
    key = "test"
    async for msg in run_client(experiment_id, duration, key):
        print("Received JSON:", msg)


if __name__ == "__main__":
    experiment_id = sys.argv[1]
    duration = 11 
    if len(sys.argv) > 2:
        duration = sys.argv[2]

    asyncio.run(main(experiment_id, duration))

