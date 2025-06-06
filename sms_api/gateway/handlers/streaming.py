import json
import os

import dotenv
import websockets
from data_model.connection import DynamicPacket

dotenv.load_dotenv()

CONNECTIONS = {}
PORT = eval(os.getenv("SERVER_PORT", "8001"))


# -- conn funcs -- #


async def open_websocket(uri: str):
    return await websockets.connect(uri)


async def listen_to_websocket(ws):
    async for message in ws:
        try:
            data = json.loads(message)
            print("Received:", data)
            # TODO: here take in the request and process, possibly also listening for deltas and stopping if so
        except json.JSONDecodeError:
            print("Invalid JSON:", message)


async def send_packet(ws, data: DynamicPacket):
    await ws.send(json.dumps(data.to_dict()))


async def receive_packet(ws, state: list):
    msg = await ws.recv()
    payload = json.loads(msg)
    state.append(payload)


async def subscribe(url: str | None = None, socket_port: int = 8765):
    async with websockets.connect(url or f"ws://localhost:{socket_port}") as websocket:
        response = await websocket.recv()
        print(f"Received from server: {response}")
        return response


async def publish(*data, url: str | None = None, socket_port: int = 8765):
    async with websockets.connect(url or f"ws://localhost:{socket_port}") as websocket:
        msg = json.dumps(data)
        await websocket.send(msg)
        print("Emitted new request!")
